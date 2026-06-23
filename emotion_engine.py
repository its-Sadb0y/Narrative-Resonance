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

_KEYWORD_MAP: Dict[str, List[str]] = {
    "joy":        ["happy", "joy", "excited", "delighted", "glad", "cheerful",
                   "pleased", "joyful", "elated", "ecstatic", "thrilled"],
    "calm":       ["calm", "peaceful", "relax", "serene", "tranquil", "quiet",
                   "soothing", "restful", "chill", "composed"],
    "nostalgia":  ["nostalgia", "remember", "memory", "childhood", "past",
                   "reminisce", "old days", "recall", "yearning"],
    "anxiety":    ["anxious", "worried", "stress", "nervous", "fear", "panic",
                   "uneasy", "tense", "apprehensive", "distressed"],
    "melancholy": ["sad", "melancholy", "lonely", "gloomy", "depressed",
                   "sorrow", "grief", "despair", "mournful"],
    "anger":      ["angry", "furious", "rage", "mad", "irritated",
                   "outraged", "resentful", "hostile", "frustrated"],
    "wonder":     ["wonder", "amazing", "surreal", "astonishing", "magical",
                   "awe", "mysterious", "fascinating", "mind-blowing"],
    "tenderness": ["love", "tender", "warm", "caring", "affectionate",
                   "compassionate", "gentle", "fond", "devoted"],
}


_NEGATION_WORDS = {"not", "no", "never", "neither", "nor", "hardly", "barely", "scarcely"}


_SINGLE_KEYWORDS: Dict[str, str] = {}
_PHRASE_KEYWORDS: List[Tuple[Pattern, str]] = []

for _emotion, _kws in _KEYWORD_MAP.items():
    for _kw in _kws:
        if " " in _kw or "-" in _kw:
            _PHRASE_KEYWORDS.append(
                (re.compile(r"\b" + re.escape(_kw) + r"\b", re.IGNORECASE), _emotion)
            )
        else:
            _SINGLE_KEYWORDS[_kw] = _emotion


_MODEL_NAME = "j-hartmann/emotion-english-distilroberta-base"

_TRANSFORMER_EMOTION_MAP: Dict[str, str] = {
    "anger":   "anger",
    "disgust": "anger",
    "fear":    "anxiety",
    "joy":     "joy",
    "neutral": "calm",
    "sadness": "melancholy",
    "surprise":"wonder",
}

_TRANSFORMER_LABELS = ["anger", "disgust", "fear", "joy", "neutral", "sadness", "surprise"]

_model = None
_tokenizer = None
_model_load_attempted = False
_model_available = False


def _ensure_model() -> bool:
    """
    Load the transformer once, on first use, and cache the outcome.

    Returns True if the model is usable. A failed/missing install is recorded
    so we don't pay the import cost again on every call.
    """
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

def _check_negation(words: List[str], keyword_index: int, window: int = 3) -> bool:
    """
    بررسی می‌کنه آیا یه کلمه‌ی negation در پنجره‌ای قبل از keyword هست.
    مثال: "not angry" → True (keyword باید ignore بشه)
    """
    start = max(0, keyword_index - window)
    preceding = words[start:keyword_index]
    return any(w.lower() in _NEGATION_WORDS for w in preceding)


def _analyze_with_keywords(text: str) -> Dict[str, float]:
    lowered = text.lower()
    words = re.findall(r"\b\w+\b", lowered)
    scores = {e: 0.0 for e in EMOTIONS}

    for idx, word in enumerate(words):
        emotion = _SINGLE_KEYWORDS.get(word)
        if emotion and not _check_negation(words, idx):
            scores[emotion] += 0.25

    for pattern, emotion in _PHRASE_KEYWORDS:
        for match in pattern.finditer(lowered):
            preceding_words = re.findall(r"\b\w+\b", lowered[:match.start()])
            if not _check_negation(preceding_words, len(preceding_words)):
                scores[emotion] += 0.25

    max_score = max(scores.values())
    if max_score > 0:
        return {k: min(v / max_score, 1.0) for k, v in scores.items()}
    return {e: 0.1 for e in EMOTIONS}


def _analyze_with_transformer(text: str) -> Dict[str, float]:
    if not _ensure_model():
        return _analyze_with_keywords(text)

    sentences = [s.strip() for s in re.split(r"[.!?]+", text) if len(s.strip()) > 5]
    if not sentences:
        return _analyze_with_keywords(text)

    aggregated = {e: 0.0 for e in EMOTIONS}
    try:
        import torch
        for sent in sentences[:10]:
            inputs = _tokenizer(sent, return_tensors="pt", truncation=True, max_length=512)
            with torch.no_grad():
                outputs = _model(**inputs)
            probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
            for i, lbl in enumerate(_TRANSFORMER_LABELS):
                mapped = _TRANSFORMER_EMOTION_MAP.get(lbl)
                if mapped:
                    aggregated[mapped] += float(probs[0][i].item())

        n = min(len(sentences), 10)
        aggregated = {k: min(v / n, 1.0) for k, v in aggregated.items()}

        if max(aggregated.values()) < 0.3:
            kw = _analyze_with_keywords(text)
            aggregated = {k: aggregated[k] * 0.6 + kw.get(k, 0) * 0.4 for k in EMOTIONS}

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
        # Clamp every value into [0, 1] and default missing keys to 0.
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
    sentences = [s.strip() for s in re.split(r"[.!?]+", text) if len(s.strip()) > 5]
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

    keyword_color_map: Dict[str, Dict] = {}
    for emotion, keywords in _KEYWORD_MAP.items():
        hue = EMOTION_HUE_MAP[emotion]
        r, g, b = colorsys.hls_to_rgb(hue / 360, 0.72, 0.65)
        hex_bg = "#{:02x}{:02x}{:02x}".format(int(r*255), int(g*255), int(b*255))
        for kw in keywords:
            keyword_color_map[kw] = {"color": hex_bg, "emotion": emotion}

    parts = re.split(r"([.!?]+)", text)
    output_parts = []

    for i in range(0, len(parts), 2):
        sent_raw = parts[i].strip()
        punct = parts[i + 1] if i + 1 < len(parts) else ""

        if not sent_raw:
            continue

        analysis = next(
            (item for item in sentence_analysis if item["sentence"] in sent_raw or sent_raw in item["sentence"]),
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
            if clean in keyword_color_map:
                try:
                    idx = word_list.index(clean)
                    negated = _check_negation(word_list, idx)
                except ValueError:
                    negated = False

                if not negated:
                    kd = keyword_color_map[clean]
                    highlighted.append(
                        f'<span style="background:{kd["color"]};padding:1px 5px;'
                        f'border-radius:3px;cursor:help;font-weight:600;color:#111;" '
                        f'title="{tooltip}">{word}</span>'
                    )
                    continue
            highlighted.append(word)

        output_parts.append("".join(highlighted) + punct)

    return " ".join(output_parts)
