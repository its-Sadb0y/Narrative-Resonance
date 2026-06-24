import os
import json
import re
import html
import colorsys
import logging
from typing import Dict, List, Optional, Tuple, Pattern

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


EMOTIONS: List[str] = [
    "joy", "calm", "nostalgia", "anxiety",
    "melancholy", "anger", "wonder", "tenderness",
    "fear", "disgust", "hope", "awe",
]


NEUTRAL = "neutral"
NEUTRAL_COLOR = "#6b6b70"


_NEUTRAL_FLOOR = 0.15

POSITIVE_EMOTIONS = {"joy", "calm", "tenderness", "wonder", "hope", "awe"}
NEGATIVE_EMOTIONS = {"anxiety", "melancholy", "anger", "fear", "disgust"}

EMOTION_HUE_MAP: Dict[str, int] = {
    "joy":        50,
    "calm":       200,
    "nostalgia":  270,
    "anxiety":    30,
    "melancholy": 220,
    "anger":      0,
    "wonder":     290,
    "tenderness": 340,
    "fear":       210,
    "disgust":    70,
    "hope":       140,
    "awe":        260,
}

EMOTION_DISPLAY_COLORS: Dict[str, str] = {
    "joy":        "#FFD700",
    "calm":       "#4A90D9",
    "nostalgia":  "#9B59B6",
    "anxiety":    "#FF6B35",
    "melancholy": "#5B4A8A",
    "anger":      "#E74C3C",
    "wonder":     "#1ABC9C",
    "tenderness": "#FF69B4",
    "fear":       "#2C3E50",
    "disgust":    "#808000",
    "hope":       "#2ECC71",
    "awe":        "#5D3FD3",
}


_LEXICON: Dict[str, Dict[str, float]] = {
    "joy": {
        "happy": 0.7, "happiness": 0.7, "happily": 0.6, "joy": 0.9, "joyful": 0.9,
        "joyous": 0.9, "glad": 0.5, "cheerful": 0.7, "cheer": 0.6, "delight": 0.8,
        "delighted": 0.85, "delightful": 0.8, "excited": 0.75, "exciting": 0.7,
        "excitement": 0.75, "thrilled": 0.9, "thrilling": 0.85, "elated": 0.95,
        "ecstatic": 1.0, "euphoric": 1.0, "pleased": 0.55, "pleasure": 0.6,
        "content": 0.4, "jubilant": 0.95, "merry": 0.6, "upbeat": 0.6,
        "gleeful": 0.8, "blissful": 0.9, "bliss": 0.9, "radiant": 0.55,
        "smiling": 0.5, "laughter": 0.6, "laughing": 0.5,
        "laugh": 0.5, "smile": 0.5, "grin": 0.55,
    },
    "calm": {
        "calm": 0.8, "calmness": 0.8, "calmly": 0.7, "peaceful": 0.8, "peace": 0.7,
        "relaxed": 0.7, "relaxing": 0.65, "relax": 0.6, "serene": 0.85,
        "serenity": 0.85, "tranquil": 0.85, "tranquility": 0.85, "quiet": 0.4,
        "soothing": 0.7, "soothe": 0.6, "restful": 0.7, "composed": 0.6,
        "settled": 0.45, "mellow": 0.55, "ease": 0.45, "untroubled": 0.7,
        "placid": 0.8, "unhurried": 0.55, "stillness": 0.5,
    },
    "nostalgia": {
        "nostalgia": 0.95, "nostalgic": 0.9, "remember": 0.5, "remembered": 0.5,
        "remembering": 0.5, "memory": 0.55, "memories": 0.55, "childhood": 0.65,
        "reminisce": 0.85, "reminiscing": 0.85, "reminiscent": 0.8, "yearning": 0.7,
        "yearn": 0.65, "longing": 0.6, "bygone": 0.8, "yesteryear": 0.85,
        "sentimental": 0.7, "wistful": 0.8, "wistfully": 0.75, "recollection": 0.6,
        "remembrance": 0.65, "old days": 0.8, "good old": 0.7, "back then": 0.6,
    },
    "anxiety": {
        "anxious": 0.85, "anxiety": 0.9, "worried": 0.75, "worry": 0.7,
        "worries": 0.7, "nervous": 0.75, "nervousness": 0.75, "stress": 0.7,
        "stressed": 0.8, "stressful": 0.75, "uneasy": 0.7, "tense": 0.7,
        "tension": 0.65, "apprehensive": 0.8, "apprehension": 0.8, "distressed": 0.85,
        "distress": 0.8, "restless": 0.65, "jittery": 0.8, "overwhelmed": 0.7,
        "on edge": 0.75, "fretful": 0.7, "edgy": 0.65,
    },
    "melancholy": {
        "sad": 0.75, "sadness": 0.8, "sadly": 0.7, "melancholy": 0.95,
        "melancholic": 0.9, "lonely": 0.8, "loneliness": 0.85, "gloomy": 0.8,
        "gloom": 0.75, "depressed": 0.9, "depression": 0.9, "sorrow": 0.9,
        "sorrowful": 0.9, "grief": 0.9, "grieving": 0.9, "despair": 0.95,
        "despairing": 0.95, "mournful": 0.85, "mourning": 0.85, "heartbroken": 0.95,
        "heartbreak": 0.9, "miserable": 0.9, "misery": 0.9, "hopeless": 0.9,
        "hopelessness": 0.9, "dejected": 0.85, "downcast": 0.75, "somber": 0.7,
        "weeping": 0.75, "crying": 0.6, "forlorn": 0.85, "bleak": 0.7, "woe": 0.85,
        "cry": 0.55, "sob": 0.7, "sobbing": 0.7, "mourn": 0.8, "wept": 0.7, "tearful": 0.7,
    },
    "anger": {
        "angry": 0.85, "anger": 0.9, "angrily": 0.8, "furious": 0.95, "fury": 0.95,
        "rage": 0.95, "raging": 0.9, "mad": 0.65, "irritated": 0.65, "irritation": 0.65,
        "irritating": 0.6, "annoyed": 0.6, "annoying": 0.55, "outraged": 0.9,
        "outrage": 0.9, "resentful": 0.8, "resentment": 0.8, "hostile": 0.8,
        "hostility": 0.8, "frustrated": 0.7, "frustration": 0.7, "livid": 0.95,
        "irate": 0.9, "enraged": 1.0, "seething": 0.9, "indignant": 0.8,
        "bitter": 0.7, "hatred": 0.9, "hate": 0.85, "wrath": 0.9,
    },
    "wonder": {
        "wonder": 0.8, "wonderful": 0.55, "wondrous": 0.85, "amazing": 0.75,
        "amazed": 0.8, "amazement": 0.85, "astonishing": 0.85, "astonished": 0.85,
        "astonishment": 0.85, "surreal": 0.8, "magical": 0.75,
        "marvel": 0.8, "marvelous": 0.7, "marvellous": 0.7,
        "mysterious": 0.7, "mystery": 0.55, "fascinating": 0.75, "fascinated": 0.75,
        "fascination": 0.75, "breathtaking": 0.9, "spellbound": 0.85,
        "enchanting": 0.8, "enchanted": 0.8,
        "mind-blowing": 0.85, "stunning": 0.7, "stunned": 0.65, "dazzling": 0.8,
        "dazzled": 0.75,
    },
    "tenderness": {
        "love": 0.85, "loved": 0.8, "loving": 0.8, "loves": 0.8, "lovely": 0.55,
        "tender": 0.85, "tenderness": 0.9, "tenderly": 0.8, "warmth": 0.55,
        "caring": 0.75, "care": 0.5, "cared": 0.55, "affection": 0.85,
        "affectionate": 0.85, "compassion": 0.85, "compassionate": 0.85,
        "gentle": 0.55, "gentleness": 0.6, "fond": 0.65, "fondness": 0.7,
        "fondly": 0.65, "devoted": 0.8, "devotion": 0.8, "cherish": 0.85,
        "cherished": 0.85, "adore": 0.9, "adored": 0.9, "adoring": 0.9,
        "comforting": 0.6, "nurturing": 0.7, "kindness": 0.6, "beloved": 0.85,
        "dear": 0.45, "intimacy": 0.7, "intimate": 0.65,
    },
    "fear": {
        "fear": 0.7, "fearful": 0.8, "afraid": 0.8, "scared": 0.8,
        "frightened": 0.85, "frightening": 0.8, "panic": 0.9, "panicked": 0.9,
        "dread": 0.85, "dreadful": 0.75, "terrified": 0.95, "terror": 0.95,
        "terrifying": 0.9, "alarmed": 0.8, "horror": 0.85, "horrified": 0.9,
        "horrifying": 0.9, "petrified": 0.95, "spooked": 0.7, "scary": 0.7,
    },
    "disgust": {
        "disgust": 0.85, "disgusted": 0.85, "disgusting": 0.85, "revolting": 0.85,
        "revolted": 0.85, "vile": 0.8, "putrid": 0.85, "foul": 0.75,
        "nauseating": 0.85, "nauseated": 0.8, "nauseous": 0.8, "repulsive": 0.85,
        "repulsed": 0.8, "gross": 0.6, "sickening": 0.8, "repugnant": 0.85,
        "rancid": 0.8, "loathing": 0.85, "loathsome": 0.85, "queasy": 0.6,
        "contempt": 0.65, "rotten": 0.55,
    },
    "hope": {
        "hope": 0.8, "hopeful": 0.85, "hopefully": 0.7, "optimistic": 0.8,
        "optimism": 0.8, "eager": 0.6, "anticipation": 0.6, "anticipate": 0.55,
        "aspire": 0.65, "aspiring": 0.65, "aspiration": 0.65, "faith": 0.5,
        "promising": 0.6, "encouraged": 0.6, "encouraging": 0.6, "uplifted": 0.7,
        "uplifting": 0.7, "reassured": 0.6, "expectant": 0.6, "looking forward": 0.65,
    },
    "awe": {
        "awe": 0.9, "awed": 0.9, "awestruck": 0.95, "sublime": 0.85,
        "reverent": 0.8, "reverence": 0.8, "majestic": 0.85, "miraculous": 0.85,
        "sacred": 0.7, "profound": 0.7, "monumental": 0.7, "immense": 0.6,
        "magnificent": 0.8, "glorious": 0.75, "grandeur": 0.8, "vast": 0.55,
    },
}


_NEGATION_WORDS = {
    "not", "no", "never", "neither", "nor", "none", "nothing", "without",
    "hardly", "barely", "scarcely",
}


_BOOSTERS = {
    "incredibly": 1.6, "extremely": 1.7, "absolutely": 1.6, "utterly": 1.6,
    "completely": 1.5, "totally": 1.4, "really": 1.3, "very": 1.3, "so": 1.25,
    "deeply": 1.4, "profoundly": 1.5, "intensely": 1.5, "terribly": 1.4,
    "awfully": 1.35, "super": 1.3, "truly": 1.3, "immensely": 1.5,
}
_DIMINISHERS = {
    "slightly": 0.5, "somewhat": 0.6, "rather": 0.75, "fairly": 0.75,
    "mildly": 0.5, "kinda": 0.6, "vaguely": 0.55, "marginally": 0.5,
}


_SINGLE_KEYWORDS: Dict[str, Tuple[str, float]] = {}
_PHRASE_KEYWORDS: List[Tuple[Pattern, str, float]] = []

for _emotion, _entries in _LEXICON.items():
    for _term, _weight in _entries.items():
        if " " in _term or "-" in _term:
            _PHRASE_KEYWORDS.append(
                (re.compile(r"\b" + re.escape(_term) + r"\b", re.IGNORECASE),
                 _emotion, _weight)
            )
        else:
            _SINGLE_KEYWORDS[_term] = (_emotion, _weight)


_MODEL_NAME = "j-hartmann/emotion-english-distilroberta-base"


_TRANSFORMER_EMOTION_MAP: Dict[str, str] = {
    "anger":    "anger",
    "fear":     "fear",
    "joy":      "joy",
    "sadness":  "melancholy",
    "surprise": "wonder",
}


_TRANSFORMER_LABELS = ["anger", "disgust", "fear", "joy", "neutral", "sadness", "surprise"]


_KEYWORD_OVERLAY: Dict[str, float] = {
    "nostalgia": 0.85,
    "tenderness": 0.85,
    "calm": 0.95,
    "melancholy": 0.80,
    "wonder": 0.60,
    "anxiety": 0.85,
    "hope": 0.80,
    "awe": 0.70,
    "disgust": 0.80,
}

_model = None
_tokenizer = None
_model_load_attempted = False
_model_available = False


def transformers_available() -> bool:
    import importlib.util
    return (
        importlib.util.find_spec("transformers") is not None
        and importlib.util.find_spec("torch") is not None
    )


def _ensure_model() -> bool:
    global _model, _tokenizer, _model_load_attempted, _model_available
    if _model_load_attempted:
        return _model_available

    _model_load_attempted = True
    try:
        from transformers import AutoTokenizer, AutoModelForSequenceClassification
        import torch

        _tokenizer = AutoTokenizer.from_pretrained(_MODEL_NAME)
        _model = AutoModelForSequenceClassification.from_pretrained(_MODEL_NAME)
        _model_available = True
        logger.info("Transformer model loaded (%s).", _MODEL_NAME)
    except ImportError:
        logger.info("transformers not installed — balanced mode falls back to keywords.")
    except Exception as e:
        logger.warning("Transformer load failed: %s", e)

    return _model_available


_ABBREVIATIONS = {
    "mr", "mrs", "ms", "dr", "prof", "sr", "jr", "st", "vs", "etc",
    "inc", "ltd", "co", "no", "vol", "fig", "gen", "sen", "rep", "gov",
}
_SENT_SENTINEL = "\u0000"


def _expand_contractions(text: str) -> str:
    text = re.sub(r"\bcan['’]t\b", "can not", text, flags=re.IGNORECASE)
    text = re.sub(r"\bwon['’]t\b", "will not", text, flags=re.IGNORECASE)
    text = re.sub(r"\bshan['’]t\b", "shall not", text, flags=re.IGNORECASE)
    text = re.sub(r"\bcannot\b", "can not", text, flags=re.IGNORECASE)
    text = re.sub(r"n['’]t\b", " not", text, flags=re.IGNORECASE)
    return text


def _split_sentences(text: str) -> List[str]:
    protected = text

    protected = re.sub(r"\b([A-Za-z])\.([A-Za-z])\.",
                       r"\1" + _SENT_SENTINEL + r"\2" + _SENT_SENTINEL, protected)
    for ab in _ABBREVIATIONS:
        protected = re.sub(rf"\b({ab})\.", r"\1" + _SENT_SENTINEL, protected, flags=re.IGNORECASE)
    protected = re.sub(r"(\d)\.(\d)", r"\1" + _SENT_SENTINEL + r"\2", protected)

    pieces = re.split(r"(?<=[.!?])\s+", protected)
    out = []
    for p in pieces:
        p = p.replace(_SENT_SENTINEL, ".").strip()
        if p:
            out.append(p)
    return out


def _normalize_candidates(word: str):
    yield word
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        yield word[:-1]
    if len(word) > 4 and word.endswith("ies"):
        yield word[:-3] + "y"
    if len(word) > 4 and word.endswith("ied"):
        yield word[:-3] + "y"
    if len(word) > 4 and word.endswith("ed"):
        yield word[:-2]
        yield word[:-1]
    if len(word) > 5 and word.endswith("ing"):
        yield word[:-3]
        yield word[:-3] + "e"


def _lexicon_hit(word: str):
    for cand in _normalize_candidates(word):
        hit = _SINGLE_KEYWORDS.get(cand)
        if hit is not None:
            return hit
    return None


def _plural_norm(word: str) -> str:
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def _context_modifier(words: List[str], idx: int, window: int = 2) -> float:
    factor = 1.0
    for w in words[max(0, idx - window):idx]:
        if w in _BOOSTERS:
            factor *= _BOOSTERS[w]
        elif w in _DIMINISHERS:
            factor *= _DIMINISHERS[w]
    return factor


def _check_negation(words: List[str], keyword_index: int, window: int = 3) -> bool:
    start = max(0, keyword_index - window)
    return any(w.lower() in _NEGATION_WORDS for w in words[start:keyword_index])


def _negated_emotions(text: str) -> set:
    lowered = _expand_contractions(text.lower())
    words = re.findall(r"\b\w+\b", lowered)
    present, negated = set(), set()
    for idx, word in enumerate(words):
        hit = _lexicon_hit(word)
        if hit is None:
            continue
        (negated if _check_negation(words, idx) else present).add(hit[0])
    for pattern, emotion, _ in _PHRASE_KEYWORDS:
        for m in pattern.finditer(lowered):
            preceding = re.findall(r"\b\w+\b", lowered[:m.start()])
            (negated if _check_negation(preceding, len(preceding)) else present).add(emotion)
    return negated - present


_HIGH_AROUSAL = {"anxiety", "anger", "joy", "wonder", "fear", "awe"}
_LOW_AROUSAL = {"calm", "melancholy", "tenderness", "nostalgia", "disgust", "hope"}


def _squash(x: float, k: float = 0.9) -> float:
    return x / (x + k) if x > 0 else 0.0


def valence_of(emotions: Dict[str, float]) -> float:
    pos = sum(emotions.get(e, 0.0) for e in POSITIVE_EMOTIONS)
    neg = sum(emotions.get(e, 0.0) for e in NEGATIVE_EMOTIONS)
    total = pos + neg
    return (pos - neg) / total if total > 0 else 0.0


def arousal_of(emotions: Dict[str, float]) -> float:
    hi = sum(emotions.get(e, 0.0) for e in _HIGH_AROUSAL)
    lo = sum(emotions.get(e, 0.0) for e in _LOW_AROUSAL)
    total = hi + lo
    return hi / total if total > 0 else 0.0


def _analyze_with_keywords(text: str, _return_raw: bool = False):
    lowered = _expand_contractions(text.lower())
    words = re.findall(r"\b\w+\b", lowered)
    scores = {e: 0.0 for e in EMOTIONS}


    for idx, word in enumerate(words):
        hit = _lexicon_hit(word)
        if hit is None:
            continue
        if _check_negation(words, idx):
            continue
        emotion, weight = hit
        scores[emotion] += weight * _context_modifier(words, idx)


    for pattern, emotion, weight in _PHRASE_KEYWORDS:
        for m in pattern.finditer(lowered):
            preceding = re.findall(r"\b\w+\b", lowered[:m.start()])
            if _check_negation(preceding, len(preceding)):
                continue
            scores[emotion] += weight * _context_modifier(preceding, len(preceding))

    max_score = max(scores.values())
    if max_score > 0:
        normalized = {k: min(v / max_score, 1.0) for k, v in scores.items()}
    else:
        normalized = {e: 0.1 for e in EMOTIONS}

    if _return_raw:
        return normalized, scores
    return normalized


def _analyze_with_transformer(text: str) -> Dict[str, float]:
    if not _ensure_model():
        return _analyze_with_keywords(text)

    sentences = [s for s in _split_sentences(text) if len(s) > 5]
    if not sentences:
        return _analyze_with_keywords(text)

    aggregated = {e: 0.0 for e in EMOTIONS}
    try:
        import torch
        cap = 400
        sentences = sentences[:cap]
        batch_size = 16

        for start in range(0, len(sentences), batch_size):
            batch = sentences[start:start + batch_size]
            inputs = _tokenizer(
                batch, return_tensors="pt", truncation=True,
                max_length=256, padding=True,
            )
            with torch.no_grad():
                logits = _model(**inputs).logits
            probs = torch.nn.functional.softmax(logits, dim=-1)
            for row in probs:
                for j, lbl in enumerate(_TRANSFORMER_LABELS):
                    mapped = _TRANSFORMER_EMOTION_MAP.get(lbl)
                    if mapped:
                        aggregated[mapped] += float(row[j].item())

        n = len(sentences)
        aggregated = {k: min(v / n, 1.0) for k, v in aggregated.items()}


        kw, kw_raw = _analyze_with_keywords(text, _return_raw=True)
        if max(kw_raw.values()) > 0:
            for emo, coeff in _KEYWORD_OVERLAY.items():
                aggregated[emo] = max(aggregated[emo], kw.get(emo, 0.0) * coeff)
            if max(aggregated.values()) < 0.3:
                aggregated = {k: aggregated[k] * 0.6 + kw.get(k, 0.0) * 0.4 for k in EMOTIONS}


        for emo in _negated_emotions(text):
            aggregated[emo] *= 0.15

        return aggregated
    except Exception as e:
        logger.warning("Transformer inference error: %s", e)
        return _analyze_with_keywords(text)


def _extract_json_object(raw: str) -> Optional[dict]:
    cleaned = raw.strip()
    cleaned = cleaned.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return None
    return None


def _analyze_with_api(text: str) -> Dict[str, float]:
    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

        truncated = text[:3000] + "..." if len(text) > 3000 else text
        keys_str = ", ".join(f'"{e}"' for e in EMOTIONS)
        prompt = (
            f"Analyze the emotional content of this text. Return ONLY a JSON object "
            f"with these exact keys: {keys_str}. "
            f"Each value is a float 0–1 representing intensity. No explanation.\n\n"
            f"Text: {truncated}"
        )
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        data = _extract_json_object(raw)
        if data is None:
            logger.warning("API returned unparseable JSON — falling back to local model.")
            return _analyze_with_transformer(text)
        return {e: max(0.0, min(1.0, float(data.get(e, 0.0)))) for e in EMOTIONS}
    except Exception as e:
        logger.warning("API error: %s — falling back to local model.", e)
        return _analyze_with_transformer(text)


def analyze_emotions(text: str, mode: str = "balanced") -> Dict[str, float]:
    if not text or len(text.strip()) < 3:
        return {e: 0.1 for e in EMOTIONS}

    if mode == "precise" and os.environ.get("ANTHROPIC_API_KEY"):
        return _analyze_with_api(text)
    if mode == "fast":
        return _analyze_with_keywords(text)
    return _analyze_with_transformer(text)


def _analyze_full(text: str, mode: str = "balanced") -> Tuple[Dict[str, float], float]:
    if not text or len(text.strip()) < 3:
        return {e: 0.1 for e in EMOTIONS}, 0.0

    if mode == "precise" and os.environ.get("ANTHROPIC_API_KEY"):
        profile = _analyze_with_api(text)
        return profile, max(profile.values())
    if mode == "fast":
        profile, raw = _analyze_with_keywords(text, _return_raw=True)
        return profile, max(raw.values())
    profile = _analyze_with_transformer(text)
    return profile, max(profile.values())


def analyze(text: str, mode: str = "balanced") -> dict:
    profile, magnitude = _analyze_full(text, mode)
    has_signal = magnitude >= _NEUTRAL_FLOOR
    if has_signal:
        dom_em, dom_sc = max(profile.items(), key=lambda x: x[1])
    else:
        dom_em, dom_sc = NEUTRAL, 0.0
    return {
        "emotions": profile,
        "dominant_emotion": dom_em,
        "dominant_score": dom_sc,
        "intensity": round(_squash(magnitude), 4),
        "valence": round(valence_of(profile), 4) if has_signal else 0.0,
        "arousal": round(arousal_of(profile), 4) if has_signal else 0.0,
    }


def emotions_to_palette(emotions: Dict[str, float], n_colors: int = 5) -> List[str]:
    if not emotions:
        raise ValueError("emotions cannot be empty")

    sorted_em = sorted(emotions.items(), key=lambda x: x[1], reverse=True)
    top3 = sorted_em[:3]

    total = sum(emotions.values())
    pos = sum(emotions.get(e, 0) for e in POSITIVE_EMOTIONS)
    neg = sum(emotions.get(e, 0) for e in NEGATIVE_EMOTIONS)

    palette = []
    for i in range(n_colors):
        primary, _ = top3[i % len(top3)]
        hue = (EMOTION_HUE_MAP.get(primary, 0) + (i * 15) - (n_colors * 7)) % 360

        avg_intensity = total / len(emotions)
        saturation = min(0.35 + avg_intensity * 0.45, 0.85)

        balance = (pos - neg) / max(total, 0.1)
        lightness = max(0.25, min(0.80,
            0.5 + balance * 0.15 + (i / max(n_colors - 1, 1)) * 0.3 - 0.15
        ))

        r, g, b = colorsys.hls_to_rgb(hue / 360, lightness, saturation)
        palette.append("#{:02x}{:02x}{:02x}".format(
            max(0, min(255, int(r * 255))),
            max(0, min(255, int(g * 255))),
            max(0, min(255, int(b * 255))),
        ))

    return palette


def text_to_palette(text: str, n_colors: int = 5, mode: str = "balanced") -> dict:
    emotions, magnitude = _analyze_full(text, mode=mode)
    palette = emotions_to_palette(emotions, n_colors=n_colors)
    if magnitude >= _NEUTRAL_FLOOR:
        dom_em, dom_sc = max(emotions.items(), key=lambda x: x[1])
    else:
        dom_em, dom_sc = NEUTRAL, 0.0
    return {
        "emotions": emotions,
        "palette": palette,
        "dominant_emotion": dom_em,
        "dominant_score": dom_sc,
    }


def analyze_emotions_by_sentence(text: str, mode: str = "balanced") -> List[Dict]:
    sentences = [s for s in _split_sentences(text) if len(s) > 5]
    if not sentences:
        return []


    raw = [(sent, *_analyze_full(sent, mode)) for sent in sentences]


    mags = sorted(m for _, _, m in raw)
    scale = mags[min(len(mags) - 1, int(0.92 * len(mags)))] if mags else 0.0
    if scale <= 0 and mags:
        scale = mags[-1]

    results = []
    for sent, emotions, magnitude in raw:
        intensity = min(magnitude / scale, 1.0) if scale > 0 else 0.0
        has_signal = magnitude >= _NEUTRAL_FLOOR
        if has_signal:
            dominant_em, dominant_sc = max(emotions.items(), key=lambda x: x[1])
            color = emotions_to_palette(emotions, n_colors=1)[0]
        else:
            dominant_em, dominant_sc = NEUTRAL, 0.0
            color = NEUTRAL_COLOR
        results.append({
            "sentence":       sent,
            "emotions":       emotions,
            "dominant":       dominant_em,
            "dominant_score": dominant_sc,
            "color":          color,
            "intensity":      round(intensity, 4),
            "valence":        round(valence_of(emotions), 4) if has_signal else 0.0,
            "arousal":        round(arousal_of(emotions), 4) if has_signal else 0.0,
        })
    return results


def highlight_keywords_html(text: str, sentence_analysis: List[Dict]) -> str:
    if not sentence_analysis:
        return text


    keyword_color_map: Dict[str, Dict] = {}
    for emotion, entries in _LEXICON.items():
        hue = EMOTION_HUE_MAP[emotion]
        r, g, b = colorsys.hls_to_rgb(hue / 360, 0.72, 0.65)
        hex_bg = "#{:02x}{:02x}{:02x}".format(int(r * 255), int(g * 255), int(b * 255))
        for kw in entries:
            keyword_color_map[kw] = {"color": hex_bg, "emotion": emotion}

    parts = re.split(r"([.!?]+)", text)
    output_parts = []

    for i in range(0, len(parts), 2):
        sent_raw = parts[i].strip()
        punct = parts[i + 1] if i + 1 < len(parts) else ""

        if not sent_raw:
            continue

        analysis = next(
            (item for item in sentence_analysis
             if item["sentence"] in sent_raw or sent_raw in item["sentence"]),
            None
        )

        if not analysis:
            output_parts.append(sent_raw + punct)
            continue

        top_emotions = sorted(analysis["emotions"].items(), key=lambda x: x[1], reverse=True)
        tooltip = " | ".join(
            f"{e.capitalize()}: {s*100:.0f}%"
            for e, s in top_emotions[:4] if s > 0.05
        )

        words = re.split(r"(\s+)", sent_raw)
        word_list = [w for w in re.findall(r"\b\w+\b", sent_raw)]
        highlighted = []

        for word in words:
            clean = re.sub(r"[^\w]", "", word.lower())
            lookup = clean if clean in keyword_color_map else _plural_norm(clean)
            if lookup in keyword_color_map:
                try:
                    idx = word_list.index(clean)
                    negated = _check_negation(word_list, idx)
                except ValueError:
                    negated = False

                if not negated:
                    kd = keyword_color_map[lookup]
                    highlighted.append(
                        f'<span style="background:{kd["color"]};padding:1px 5px;'
                        f'border-radius:3px;cursor:help;font-weight:600;color:#111;" '
                        f'title="{tooltip}">{word}</span>'
                    )
                    continue
            highlighted.append(word)

        output_parts.append("".join(highlighted) + punct)

    return " ".join(output_parts)


def _hex_to_rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{round(alpha, 3)})"


def shade_sentences_html(text: str, sentence_analysis: List[Dict]) -> str:
    if not sentence_analysis:
        return html.escape(text).replace("\n", "<br>")

    out, cursor = [], 0
    for item in sentence_analysis:
        sent = item["sentence"]
        pos = text.find(sent, cursor)
        if pos == -1:
            continue

        out.append(html.escape(text[cursor:pos]))

        emotion = item["dominant"]
        intensity = max(0.0, min(1.0, item.get("intensity", 0.0)))

        if intensity < 0.04:
            out.append(html.escape(sent))
            cursor = pos + len(sent)
            continue

        color = EMOTION_DISPLAY_COLORS.get(emotion, "#888888")
        bg = _hex_to_rgba(color, 0.06 + 0.44 * intensity)

        top = sorted(item["emotions"].items(), key=lambda x: x[1], reverse=True)[:3]
        tip = " · ".join(f"{e.capitalize()} {int(s * 100)}%" for e, s in top if s > 0.05)

        out.append(
            f'<span title="{tip}" style="background:{bg};'
            f'box-shadow:inset 3px 0 0 {color};border-radius:3px;'
            f'padding:1px 4px;transition:background .2s;">'
            f'{html.escape(sent)}</span>'
        )
        cursor = pos + len(sent)

    out.append(html.escape(text[cursor:]))
    return "".join(out).replace("\n", "<br>")
