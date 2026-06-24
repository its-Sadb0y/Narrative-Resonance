from math import ceil
from typing import Dict, List, Optional

from emotion_engine import (
    analyze_emotions_by_sentence,
    emotions_to_palette,
    EMOTIONS,
    EMOTION_DISPLAY_COLORS,
    NEUTRAL,
    NEUTRAL_COLOR,
)


_MIN_GLOW = 0.18


def _aggregate(emotion_dicts: List[Dict[str, float]]) -> Dict[str, float]:
    agg = {e: 0.0 for e in EMOTIONS}
    for em in emotion_dicts:
        for k, v in em.items():
            agg[k] += v
    n = len(emotion_dicts) or 1
    return {k: v / n for k, v in agg.items()}


def build_fingerprint(
    text: str,
    mode: str = "balanced",
    max_columns: int = 120,
) -> List[Dict]:
    rows = analyze_emotions_by_sentence(text, mode=mode)
    if not rows:
        return []

    n = len(rows)
    if n <= max_columns:
        bins = [[r] for r in rows]
    else:
        size = ceil(n / max_columns)
        bins = [rows[i:i + size] for i in range(0, n, size)]

    columns = []
    cursor = 0
    for b in bins:
        agg = _aggregate([r["emotions"] for r in b])


        mean_i = sum(r["intensity"] for r in b) / len(b)
        peak_i = max(r["intensity"] for r in b)
        intensity = 0.45 * mean_i + 0.55 * peak_i
        valence = sum(r["valence"] for r in b) / len(b)
        arousal = sum(r["arousal"] for r in b) / len(b)
        dominant = max(agg.items(), key=lambda x: x[1])[0]
        if intensity < 0.05:
            dominant = NEUTRAL
            color = NEUTRAL_COLOR
        else:
            color = EMOTION_DISPLAY_COLORS.get(dominant, emotions_to_palette(agg, 1)[0])
        columns.append({
            "color":     color,
            "intensity": round(intensity, 4),
            "valence":   round(valence, 4),
            "arousal":   round(arousal, 4),
            "dominant":  dominant,
            "span":      (cursor, cursor + len(b) - 1),
        })
        cursor += len(b)
    return columns


def fingerprint_svg(
    columns: List[Dict],
    width: int = 900,
    height: int = 120,
    gap: float = 0.0,
    rounded: bool = True,
) -> str:
    if not columns:
        return ""

    n = len(columns)
    col_w = width / n
    radius = 14 if rounded else 0

    rects = []
    for i, c in enumerate(columns):
        x = i * col_w
        glow = _MIN_GLOW + (1 - _MIN_GLOW) * max(0.0, min(1.0, c["intensity"]))
        title = f'{c["dominant"].capitalize()} · intensity {int(c["intensity"]*100)}%'
        rects.append(
            f'<rect x="{x:.2f}" y="0" width="{col_w - gap:.2f}" height="{height}" '
            f'fill="{c["color"]}" opacity="{glow:.3f}">'
            f'<title>{title}</title></rect>'
        )

    return (
        f'<svg viewBox="0 0 {width} {height}" width="100%" '
        f'preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg" '
        f'style="border-radius:{radius}px;display:block;">'
        f'<rect width="{width}" height="{height}" fill="#0c0c0f"/>'
        + "".join(rects) +
        '</svg>'
    )


def text_to_fingerprint_svg(
    text: str,
    mode: str = "balanced",
    max_columns: int = 120,
    width: int = 900,
    height: int = 120,
) -> Optional[str]:
    cols = build_fingerprint(text, mode=mode, max_columns=max_columns)
    if not cols:
        return None
    return fingerprint_svg(cols, width=width, height=height)
