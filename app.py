import streamlit as st
import plotly.graph_objects as go

from emotion_engine import (
    text_to_palette,
    analyze_emotions_by_sentence,
    highlight_keywords_html,
    EMOTIONS,
    EMOTION_DISPLAY_COLORS,
    transformers_available,
)

st.set_page_config(
    page_title="Emotion Palette",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
/* ── Layout ── */
.block-container { padding-top: 2rem; max-width: 960px; }

/* ── Palette card ── */
.palette-wrap {
    display: flex;
    gap: 10px;
    margin-top: 6px;
}
.swatch {
    flex: 1;
    border-radius: 10px;
    height: 80px;
    transition: transform .15s;
}
.swatch:hover { transform: scaleY(1.06); }
.hex-label {
    text-align: center;
    font-family: monospace;
    font-size: 12px;
    margin-top: 5px;
    opacity: 0.75;
}

/* ── Keyword highlight container ── */
.kw-box {
    padding: 16px 20px;
    border-radius: 10px;
    font-size: 15px;
    line-height: 2.1;
    border: 1px solid rgba(128,128,128,0.2);
}

/* ── Emotion bar ── */
.em-row {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 6px;
}
.em-label { width: 96px; font-size: 13px; opacity: .85; }
.em-bar-wrap { flex: 1; background: rgba(128,128,128,.12); border-radius: 6px; height: 10px; }
.em-bar { height: 10px; border-radius: 6px; }
.em-pct { width: 36px; font-size: 12px; text-align: right; opacity: .65; font-family: monospace; }

/* ── Section divider ── */
.divider { border: none; border-top: 1px solid rgba(128,128,128,.15); margin: 1.5rem 0; }
</style>
""", unsafe_allow_html=True)


st.title("🎨 Emotion Palette Generator")
st.caption("Write any text — discover its emotional color palette, arc, and highlighted keywords.")

with st.sidebar:
    st.header("⚙️ Settings")

    has_transformers = transformers_available()

    n_colors = st.slider("Palette size", min_value=3, max_value=8, value=5)

    mode_labels = {"fast": "⚡ Fast (keywords only)"}
    if has_transformers:
        mode_labels["balanced"] = "🧠 Balanced (transformer)"
    mode_labels["precise"] = "🎯 Precise (Claude API)"

    default_mode = "balanced" if has_transformers else "fast"
    mode = st.selectbox(
        "Analysis mode",
        options=list(mode_labels.keys()),
        format_func=lambda x: mode_labels[x],
        index=list(mode_labels.keys()).index(default_mode),
    )

    if mode == "precise":
        api_key = st.text_input("Anthropic API Key", type="password", placeholder="sk-ant-...")
        if api_key:
            import os; os.environ["ANTHROPIC_API_KEY"] = api_key

    st.markdown("---")
    st.markdown("""
**How it works**

Each emotion maps to a region on the HSL color wheel:
- **Hue** ← dominant emotion type
- **Saturation** ← overall emotional intensity
- **Lightness** ← positive vs. negative balance
""")

text_input = st.text_area(
    "Your text",
    placeholder="e.g., The gentle rain brought back childhood memories of a quieter time...",
    height=130,
    label_visibility="collapsed",
)

col_btn, col_hint = st.columns([1, 5])
with col_btn:
    generate = st.button("Generate →", type="primary", use_container_width=True)
with col_hint:
    st.caption("Tip: longer texts produce richer emotional arcs.")

if generate:
    if not text_input.strip():
        st.warning("Please enter some text first.")
        st.stop()

    with st.spinner("Analyzing emotions…"):
        result = text_to_palette(text_input, n_colors=n_colors, mode=mode)
        sentence_data = analyze_emotions_by_sentence(text_input, mode=mode)

    emotions = result["emotions"]
    palette  = result["palette"]

    st.markdown("<hr class='divider'>", unsafe_allow_html=True)
    st.subheader("🎨 Color Palette")

    swatches_html = '<div class="palette-wrap">'
    for color in palette:
        swatches_html += f'<div class="swatch" style="background:{color};" title="{color}"></div>'
    swatches_html += "</div>"
    hex_row = '<div class="palette-wrap">'
    for color in palette:
        hex_row += f'<div style="flex:1;" class="hex-label">{color}</div>'
    hex_row += "</div>"

    st.markdown(swatches_html + hex_row, unsafe_allow_html=True)

    css_vars = "\n".join(f"  --palette-{i+1}: {c};" for i, c in enumerate(palette))
    with st.expander("Copy as CSS variables"):
        st.code(f":root {{\n{css_vars}\n}}", language="css")

    st.markdown("<hr class='divider'>", unsafe_allow_html=True)
    left, right = st.columns([1, 1])

    with left:
        st.subheader("🎭 Emotion Breakdown")
        sorted_em = sorted(emotions.items(), key=lambda x: x[1], reverse=True)
        bars_html = ""
        for em, score in sorted_em:
            if score < 0.02:
                continue
            bar_color = EMOTION_DISPLAY_COLORS.get(em, "#888")
            pct = int(score * 100)
            bars_html += (
                f'<div class="em-row">'
                f'<span class="em-label">{em.capitalize()}</span>'
                f'<div class="em-bar-wrap">'
                f'<div class="em-bar" style="width:{pct}%;background:{bar_color};"></div>'
                f'</div>'
                f'<span class="em-pct">{pct}%</span>'
                f'</div>'
            )
        st.markdown(bars_html, unsafe_allow_html=True)

    with right:
        st.subheader("📊 Dominant emotion")
        dom = result["dominant_emotion"]
        dom_score = result["dominant_score"]
        dom_color = EMOTION_DISPLAY_COLORS.get(dom, "#888")
        st.markdown(
            f'<div style="background:{dom_color}22;border-left:4px solid {dom_color};'
            f'padding:16px 20px;border-radius:8px;margin-top:8px;">'
            f'<div style="font-size:32px;font-weight:700;color:{dom_color};">'
            f'{dom.capitalize()}</div>'
            f'<div style="opacity:.7;margin-top:4px;">{dom_score*100:.0f}% intensity</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    st.markdown("<hr class='divider'>", unsafe_allow_html=True)
    st.subheader("📈 Emotional Arc")

    if len(sentence_data) < 2:
        st.info("Add more sentences to see how emotions evolve throughout your text.")
    else:
        labels = [f"S{i+1}" for i in range(len(sentence_data))]
        fig = go.Figure()

        for em in EMOTIONS:
            scores = [item["emotions"].get(em, 0) for item in sentence_data]
            if max(scores) <= 0.1:
                continue
            fig.add_trace(go.Scatter(
                x=labels, y=scores,
                mode="lines+markers",
                name=em.capitalize(),
                line=dict(width=2, color=EMOTION_DISPLAY_COLORS.get(em, "#888")),
                marker=dict(size=7),
                hovertemplate="<b>%{x}</b> — %{y:.0%}<extra></extra>",
            ))

        fig.update_layout(
            height=340,
            margin=dict(l=10, r=10, t=10, b=10),
            hovermode="x unified",
            yaxis=dict(range=[0, 1], tickformat=".0%", gridcolor="rgba(128,128,128,.1)"),
            xaxis=dict(gridcolor="rgba(128,128,128,.1)"),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", y=-0.2),
            font=dict(size=12),
        )
        st.plotly_chart(fig, use_container_width=True)

        with st.expander("Sentence breakdown"):
            for i, item in enumerate(sentence_data):
                c = item["color"]
                badge = (
                    f'<span style="background:{c};color:#111;padding:2px 10px;'
                    f'border-radius:10px;font-weight:600;font-size:12px;">'
                    f'{item["dominant"].capitalize()} {item["dominant_score"]*100:.0f}%</span>'
                )
                st.markdown(f"**S{i+1}** {badge} &nbsp; *{item['sentence']}*", unsafe_allow_html=True)

    st.markdown("<hr class='divider'>", unsafe_allow_html=True)
    st.subheader("📝 Keyword Highlighting")
    st.caption("Emotional keywords are highlighted — hover for sentence-level analysis.")

    highlighted = highlight_keywords_html(text_input, sentence_data)
    st.markdown(f'<div class="kw-box">{highlighted}</div>', unsafe_allow_html=True)
