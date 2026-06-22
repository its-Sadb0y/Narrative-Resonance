"""
emotion_engine.py — Core emotion analysis and color palette mapping.

سه سطح تحلیل:
  fast     → keyword-based (بدون نیاز به هیچ چیز اضافه)
  balanced → transformer محلی (نیاز به: pip install transformers torch)
  precise  → Claude API     (نیاز به: ANTHROPIC_API_KEY)
"""

import os
import json
import re
import colorsys
import sys
import io
from typing import Dict, List

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ─────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────

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

# رنگ نمایشی ثابت برای هر احساس (برای نمودار arc و legend)
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

# کلماتی که negation می‌کنن احساس بعدیشون رو
_NEGATION_WORDS = {"not", "no", "never", "neither", "nor", "hardly", "barely", "scarcely"}

# ─────────────────────────────────────────────
# Optional: Transformer model
# ─────────────────────────────────────────────

_model = None
_tokenizer = None
_HAS_TRANSFORMERS = False

# این mapping خارج از try block تعریف شده تا همیشه قابل دسترس باشه
_TRANSFORMER_EMOTION_MAP: Dict[str, str] = {
    "anger":   "anger",
    "disgust": "anger",
    "fear":    "anxiety",
    "joy":     "joy",
    "neutral": "calm",
    "sadness": "melancholy",
    "surprise":"wonder",
}

try:
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    import torch

    _model_name = "j-hartmann/emotion-english-distilroberta-base"
    _tokenizer = AutoTokenizer.from_pretrained(_model_name)
    _model = AutoModelForSequenceClassification.from_pretrained(_model_name)
    _HAS_TRANSFORMERS = True
    print("[OK] Transformer model loaded.")
except ImportError:
    print("[INFO] Transformers not installed — using keyword engine (fast mode).")
except Exception as e:
    print(f"[WARN] Transformer load failed: {e}")

# ─────────────────────────────────────────────
# Internal analysis helpers
# ─────────────────────────────────────────────

def _check_negation(words: List[str], keyword_index: int, window: int = 3) -> bool:
    """
    بررسی می‌کنه آیا یه کلمه‌ی negation در پنجره‌ای قبل از keyword هست.
    مثال: "not angry" → True (keyword باید ignore بشه)
    """
    start = max(0, keyword_index - window)
    preceding = words[start:keyword_index]
    return any(w.lower() in _NEGATION_WORDS for w in preceding)


def _analyze_with_keywords(text: str) -> Dict[str, float]:
    """
    تحلیل keyword-based با negation detection.
    مثال: 'not angry' → anger افزایش پیدا نمی‌کنه
    """
    words = re.findall(r'\b\w+\b', text.lower())
    scores = {e: 0.0 for e in EMOTIONS}

    for emotion, keywords in _KEYWORD_MAP.items():
        for kw in keywords:
            kw_words = kw.split()
            if len(kw_words) == 1:
                # single-word keyword
                for idx, word in enumerate(words):
                    if word == kw:
                        if not _check_negation(words, idx):
                            scores[emotion] += 0.25
            else:
                # multi-word phrase (مثل "old days")
                phrase_str = " ".join(kw_words)
                count = text.lower().count(phrase_str)
                if count > 0:
                    scores[emotion] += count * 0.25

    max_score = max(scores.values())
    if max_score > 0:
        return {k: min(v / max_score, 1.0) for k, v in scores.items()}
    return {e: 0.1 for e in EMOTIONS}


def _analyze_with_transformer(text: str) -> Dict[str, float]:
    if not _HAS_TRANSFORMERS or _model is None or _tokenizer is None:
        return _analyze_with_keywords(text)

    sentences = [s.strip() for s in re.split(r'[.!?]+', text) if len(s.strip()) > 5]
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
            label_names = ["anger", "disgust", "fear", "joy", "neutral", "sadness", "surprise"]
            for i, lbl in enumerate(label_names):
                mapped = _TRANSFORMER_EMOTION_MAP.get(lbl)
                if mapped:
                    aggregated[mapped] += float(probs[0][i].item())

        n = len(sentences)
        aggregated = {k: min(v / n, 1.0) for k, v in aggregated.items()}

        # اگه مدل نتیجه‌ی ضعیفی داد، keyword رو blend کن
        if max(aggregated.values()) < 0.3:
            kw = _analyze_with_keywords(text)
            aggregated = {k: aggregated[k] * 0.6 + kw.get(k, 0) * 0.4 for k in EMOTIONS}

        return aggregated
    except Exception as e:
        print(f"[WARN] Transformer error: {e}")
        return _analyze_with_keywords(text)


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
        raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        data = json.loads(raw)
        return {e: float(data.get(e, 0.0)) for e in EMOTIONS}
    except Exception as e:
        print(f"[WARN] API error: {e} — falling back to local model.")
        return _analyze_with_transformer(text)


# ─────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────

def analyze_emotions(text: str, mode: str = "balanced") -> Dict[str, float]:
    """
    تحلیل احساسات یه متن.
    mode: "fast" | "balanced" | "precise"
    """
    if not text or len(text.strip()) < 3:
        return {e: 0.1 for e in EMOTIONS}

    if mode == "precise" and os.environ.get("ANTHROPIC_API_KEY"):
        return _analyze_with_api(text)
    if mode == "fast" or not _HAS_TRANSFORMERS:
        return _analyze_with_keywords(text)
    return _analyze_with_transformer(text)


def emotions_to_palette(emotions: Dict[str, float], n_colors: int = 5) -> List[str]:
    """
    دیکشنری احساسات → لیست رنگ‌های HEX.

    منطق نگاشت:
      Hue        ← نوع احساس غالب (با کمی drift برای تنوع در پالت)
      Saturation ← شدت میانگین احساسات (قوی‌تر = پررنگ‌تر)
      Lightness  ← تعادل مثبت/منفی (مثبت = روشن‌تر)
    """
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
        hue = (EMOTION_HUE_MAP[primary] + (i * 15) - (n_colors * 7)) % 360

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
    """تابع high-level: متن → احساسات + پالت رنگی."""
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
    """
    متن رو جمله‌به‌جمله تحلیل می‌کنه.
    برای رسم Emotional Arc و keyword highlighting استفاده می‌شه.
    """
    sentences = [s.strip() for s in re.split(r'[.!?]+', text) if len(s.strip()) > 5]
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
    """
    کلمات کلیدی احساسی رو با رنگ و tooltip HTML هایلایت می‌کنه.
    خروجی: رشته‌ی HTML آماده برای نمایش.
    """
    if not sentence_analysis:
        return text

    # ساخت keyword → {color, emotion}
    keyword_color_map: Dict[str, Dict] = {}
    for emotion, keywords in _KEYWORD_MAP.items():
        hue = EMOTION_HUE_MAP[emotion]
        r, g, b = colorsys.hls_to_rgb(hue / 360, 0.72, 0.65)
        hex_bg = "#{:02x}{:02x}{:02x}".format(int(r*255), int(g*255), int(b*255))
        for kw in keywords:
            keyword_color_map[kw] = {"color": hex_bg, "emotion": emotion}

    # پردازش جمله به جمله
    parts = re.split(r'([.!?]+)', text)
    output_parts = []

    for i in range(0, len(parts), 2):
        sent_raw = parts[i].strip()
        punct = parts[i + 1] if i + 1 < len(parts) else ""

        if not sent_raw:
            continue

        # پیدا کردن analysis متناظر
        analysis = next(
            (item for item in sentence_analysis if item["sentence"] in sent_raw or sent_raw in item["sentence"]),
            None
        )

        if not analysis:
            output_parts.append(sent_raw + punct)
            continue

        # ساخت tooltip
        top_emotions = sorted(analysis["emotions"].items(), key=lambda x: x[1], reverse=True)
        tooltip = " | ".join(
            f"{e.capitalize()}: {s*100:.0f}%"
            for e, s in top_emotions[:4] if s > 0.05
        )

        # هایلایت کلمات
        words = re.split(r'(\s+)', sent_raw)
        word_list = [w for w in re.findall(r'\b\w+\b', sent_raw)]
        highlighted = []

        for word in words:
            clean = re.sub(r'[^\w]', '', word.lower())
            if clean in keyword_color_map:
                # چک negation: پیدا کردن index کلمه در لیست
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
