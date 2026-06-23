import os
import json
import re
import colorsys
import logging
from typing import Dict, List, Optional, Tuple, Pattern

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

EMOTIONS: List[str] = [
    "joy", "calm", "nostalgia", "anxiety",
    "melancholy", "anger", "wonder", "tenderness",
]

POSITIVE_EMOTIONS = {"joy", "calm", "tenderness", "wonder"}
NEGATIVE_EMOTIONS = {"anxiety", "melancholy", "anger"}

EMOTION_HUE_MAP: Dict[str, int] = {
    "joy":        50,
    "calm":       200,
    "nostalgia":  270,
    "anxiety":    30,
    "melancholy": 220,
    "anger":      0,
    "wonder":     290,
    "tenderness": 340,
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
        "stressed": 0.8, "stressful": 0.75, "fear": 0.7, "fearful": 0.8,
        "afraid": 0.75, "scared": 0.8, "frightened": 0.85, "panic": 0.9,
        "panicked": 0.9, "dread": 0.85, "uneasy": 0.7, "tense": 0.7,
        "tension": 0.65, "apprehensive": 0.8, "apprehension": 0.8, "distressed": 0.85,
        "distress": 0.8, "restless": 0.65, "jittery": 0.8, "overwhelmed": 0.7,
        "terrified": 0.95, "alarmed": 0.8, "on edge": 0.75,
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
    },
    "anger": {
        "angry": 0.85, "anger": 0.9, "angrily": 0.8, "furious": 0.95, "fury": 0.95,
        "rage": 0.95, "raging": 0.9, "mad": 0.65, "irritated": 0.65, "irritation": 0.65,
        "irritating": 0.6, "annoyed": 0.6, "annoying": 0.55, "outraged": 0.9,
        "outrage": 0.9, "resentful": 0.8, "resentment": 0.8, "hostile": 0.8,
        "hostility": 0.8, "frustrated": 0.7, "frustration": 0.7, "livid": 0.95,
        "irate": 0.9, "enraged": 1.0, "seething": 0.9, "indignant": 0.8,
        "bitter": 0.7, "hatred": 0.9, "hate": 0.85, "disgusted": 0.8, "disgust": 0.8,
        "contempt": 0.8, "wrath": 0.9,
    },
    "wonder": {
        "wonder": 0.8, "wonderful": 0.55, "wondrous": 0.85, "amazing": 0.75,
        "amazed": 0.8, "amazement": 0.85, "astonishing": 0.85, "astonished": 0.85,
        "astonishment": 0.85, "surreal": 0.8, "magical": 0.75, "awe": 0.9,
        "awestruck": 0.95, "marvel": 0.8, "marvelous": 0.7, "marvellous": 0.7,
        "mysterious": 0.7, "mystery": 0.55, "fascinating": 0.75, "fascinated": 0.75,
        "fascination": 0.75, "breathtaking": 0.9, "spellbound": 0.85,
        "enchanting": 0.8, "enchanted": 0.8, "miraculous": 0.85, "sublime": 0.85,
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

# Maps the model's 7 labels onto our taxonomy. NOTE: the model has no signal
# for "nostalgia" or "tenderness" — those are sourced from the lexicon instead.
_TRANSFORMER_EMOTION_MAP: Dict[str, str] = {
    "anger":    "anger",
    "disgust":  "anger",
    "fear":     "anxiety",
    "joy":      "joy",
    "neutral":  "calm",
    "sadness":  "melancholy",
    "surprise": "wonder",
}
_TRANSFORMER_LABELS = ["anger", "disgust", "fear", "joy", "neutral", "sadness", "surprise"]
_KEYWORD_OVERLAY: Dict[str, float] = {
    "nostalgia": 0.85,
    "tenderness": 0.85,
    "calm": 0.60,
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
        import torch  # noqa: F401

        _tokenizer = AutoTokenizer.from_pretrained(_MODEL_NAME)
        _model = AutoModelForSequenceClassification.from_pretrained(_MODEL_NAME)
        _model_available = True
        logger.info("Transformer model loaded (%s).", _MODEL_NAME)
    except ImportError:
        logger.info("transformers not installed — balanced mode falls back to keywords.")
    except Exception as e:  # noqa: BLE001
        logger.warning("Transformer load failed: %s", e)

    return _model_available

_ABBREVIATIONS = {
    "mr", "mrs", "ms", "dr", "prof", "sr", "jr", "st", "vs", "etc",
    "inc", "ltd", "co", "no", "vol", "fig", "gen", "sen", "rep", "gov",
}
_SENT_SENTINEL = "\u0000"


def _expand_contractions(text: str) -> str:
    """Normalise negated contractions so 'wasn't' tokenises to 'was not'."""
    text = re.sub(r"\bcan['’]t\b", "can not", text, flags=re.IGNORECASE)
    text = re.sub(r"\bwon['’]t\b", "will not", text, flags=re.IGNORECASE)
    text = re.sub(r"\bshan['’]t\b", "shall not", text, flags=re.IGNORECASE)
    text = re.sub(r"\bcannot\b", "can not", text, flags=re.IGNORECASE)
    text = re.sub(r"n['’]t\b", " not", text, flags=re.IGNORECASE)
    return text


def _split_sentences(text: str) -> List[str]:
    protected = text
    for ab in _ABBREVIATIONS:
        protected = re.sub(rf"\b({ab})\.", r"\1" + _SENT_SENTINEL, protected, flags=re.IGNORECASE)
    protected = re.sub(r"(\d)\.(\d)", r"\1" + _SENT_SENTINEL + r"\2", protected)  # decimals

    pieces = re.split(r"(?<=[.!?])\s+", protected)
    out = []
    for p in pieces:
        p = p.replace(_SENT_SENTINEL, ".").strip()
        if p:
            out.append(p)
    return out


def _plural_norm(word: str) -> str:
    """Conservative recall fallback: drop a regular trailing plural -s."""
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def _context_modifier(words: List[str], idx: int, window: int = 2) -> float:
    """Scale a keyword's weight by nearby boosters / diminishers."""
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

def _analyze_with_keywords(text: str) -> Dict[str, float]:
    lowered = _expand_contractions(text.lower())
    words = re.findall(r"\b\w+\b", lowered)
    scores = {e: 0.0 for e in EMOTIONS}

    for idx, word in enumerate(words):
        hit = _SINGLE_KEYWORDS.get(word)
        if hit is None:
            hit = _SINGLE_KEYWORDS.get(_plural_norm(word))
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
        return {k: min(v / max_score, 1.0) for k, v in scores.items()}
    return {e: 0.1 for e in EMOTIONS}


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

        kw = _analyze_with_keywords(text)
        for emo, coeff in _KEYWORD_OVERLAY.items():
            aggregated[emo] = max(aggregated[emo], kw.get(emo, 0.0) * coeff)

        if max(aggregated.values()) < 0.3:
            aggregated = {k: aggregated[k] * 0.6 + kw.get(k, 0.0) * 0.4 for k in EMOTIONS}

        return aggregated
    except Exception as e:
        logger.warning("Transformer inference error: %s", e)
        return _analyze_with_keywords(text)


def _extract_json_object(raw: str) -> Optional[dict]:
    """Parse a JSON object from a model reply, tolerating fences or stray prose."""
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
    except Exception as e:  # noqa: BLE001
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
    emotions = analyze_emotions(text, mode=mode)
    palette = emotions_to_palette(emotions, n_colors=n_colors)
    dominant = max(emotions.items(), key=lambda x: x[1])
    return {
        "emotions": emotions,
        "palette": palette,
        "dominant_emotion": dominant[0],
        "dominant_score": dominant[1],
    }


def analyze_emotions_by_sentence(text: str, mode: str = "balanced") -> List[Dict]:
    sentences = [s for s in _split_sentences(text) if len(s) > 5]
    if not sentences:
        return []

    results = []
    for sent in sentences:
        emotions = analyze_emotions(sent, mode=mode)
        dominant_em, dominant_sc = max(emotions.items(), key=lambda x: x[1])
        color = emotions_to_palette(emotions, n_colors=1)[0]
        results.append({
            "sentence":       sent,
            "emotions":       emotions,
            "dominant":       dominant_em,
            "dominant_score": dominant_sc,
            "color":          color,
        })
    return results


def highlight_keywords_html(text: str, sentence_analysis: List[Dict]) -> str:
    if not sentence_analysis:
        return text

    # keyword → {color, emotion}
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
