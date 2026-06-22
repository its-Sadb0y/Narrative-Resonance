# Contributing

Contributions are welcome — especially around the color mapping algorithm and lexicon expansion.

## Setup

```bash
git clone https://github.com/YOUR_USERNAME/emotion-palette
cd emotion-palette
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

## Areas open for contribution

- **Expanding the keyword lexicon** in `emotion_engine.py` (`_KEYWORD_MAP`) — more languages, more nuance
- **Improving the HSL mapping algorithm** in `emotions_to_palette()` — the current formula is a starting point
- **Phase 2: Narrative Arc** — see the roadmap in README
- **Tests** — there are currently no unit tests; adding them would be very useful

## Code style

- Keep `emotion_engine.py` free of any UI/Streamlit imports
- New analysis backends should follow the `_analyze_with_*` pattern and be wired into `analyze_emotions()`
