# 🎨 Emotion Palette Generator

> *What color is your text?*

An NLP tool that reads the emotional content of any text and translates it into a unique color palette — not through simple emotion→color mappings ("anger = red"), but by encoding a multi-dimensional emotional vector into the HSL color space.

---

## How it works

```
Text → Emotion Vector (8 dimensions) → HSL Mapping → Color Palette
```

Each of the 8 emotions maps to a specific region of the color wheel:

| Emotion | Hue | Emotion | Hue |
|---|---|---|---|
| Joy | 50° (warm yellow) | Anxiety | 30° (sharp orange) |
| Calm | 200° (soft blue) | Anger | 0° (red) |
| Nostalgia | 270° (violet) | Wonder | 290° (violet-pink) |
| Melancholy | 220° (dark blue) | Tenderness | 340° (rose) |

Then three HSL dimensions are derived from the emotion vector:
- **Hue** ← dominant emotion type (with slight drift per swatch for variety)
- **Saturation** ← overall emotional intensity (stronger feelings = more vivid colors)
- **Lightness** ← balance of positive vs. negative emotions

The result is a palette that is mathematically derived from meaning — two texts with similar emotional profiles produce similar palettes, while opposite moods produce complementary or contrasting colors.

---

## Features

- **Color Palette** — 3–8 swatches with HEX codes, exportable as CSS variables
- **Emotion Breakdown** — intensity bar chart for all 8 emotion dimensions
- **Emotional Arc** — sentence-by-sentence evolution chart (Plotly)
- **Keyword Highlighting** — emotional keywords highlighted with hover tooltips
- **Three analysis modes** depending on what you have installed

---

## Analysis modes

| Mode | How | Quality | Requirement |
|---|---|---|---|
| ⚡ Fast | Keyword matching + negation detection | Basic | None |
| 🧠 Balanced | Local transformer (`distilroberta`) | Good | `transformers` + `torch` |
| 🎯 Precise | Claude API | Best | `ANTHROPIC_API_KEY` |

The app auto-selects the best available mode. All modes work offline except Precise.

---

## Quick start

```bash
git clone https://github.com/YOUR_USERNAME/emotion-palette
cd emotion-palette

pip install -r requirements.txt

streamlit run app.py
```

**Optional — for Balanced mode:**
```bash
pip install transformers torch
```

**Optional — for Precise mode:**
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```
Or enter your key directly in the app sidebar.

---

## Project structure

```
emotion-palette/
├── app.py                  # Streamlit UI
├── emotion_engine.py       # Core logic (analysis + color mapping)
├── requirements.txt
├── .streamlit/
│   └── config.toml         # Theme config
└── .gitignore
```

`emotion_engine.py` is intentionally decoupled from the UI so it can be used as a standalone library or imported in Phase 2 of the project.

---

## Roadmap

- [x] **Phase 1** — Color palette extraction from text
- [ ] **Phase 2** — Narrative Emotion Arc: visualize emotional evolution across a full novel or screenplay, paragraph by paragraph

---

## License

MIT
