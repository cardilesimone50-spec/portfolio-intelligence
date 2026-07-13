"""Componenti UI riusabili: hero, card, sezioni, breakdown, landing."""

import streamlit as st

from src.visualization.charts import GAIN, LOSS

AMBER = "#f7a600"


def eur(value: float) -> str:
    return f"{value:,.0f} €".replace(",", ".")


def sec(title: str) -> None:
    """Etichetta di sezione con barretta ambra."""
    st.markdown(f'<div class="sec">{title}</div>', unsafe_allow_html=True)


def _status_color(score: float) -> str:
    return GAIN if score >= 67 else AMBER if score >= 34 else LOSS


def hero_html(
    health: int, value: str, change: float, period: str,
    today_move: float | None = None,
) -> str:
    gauge_color = _status_color(health)
    arrow, css = ("▲", "up") if change >= 0 else ("▼", "down")
    today_html = ""
    if today_move is not None and today_move == today_move:
        arrow_t, css_t = ("▲", "up") if today_move >= 0 else ("▼", "down")
        today_html = (
            f'<div class="chg {css_t}" style="font-size:.85rem;margin-top:2px">'
            f'Ultima seduta {arrow_t} {today_move:+.2%}</div>'
        )
    return f"""
    <div class="hero-panel" style="--val:{health}; --gcol:{gauge_color}">
      <div class="gauge"><div class="gauge-inner">
        <span class="gauge-num">{health}</span>
        <span class="gauge-sub">HEALTH /100</span>
      </div></div>
      <div class="hero-meta">
        <div class="label">Valore stimato</div>
        <div class="big">{value}</div>
        <div class="chg {css}">{arrow} {change:+.1%} · {period}</div>
        {today_html}
      </div>
    </div>"""


def dna_card_html(dna: dict[str, float], label: str, title: str = "PORTFOLIO DNA") -> str:
    rows = ""
    for name, score in dna.items():
        css = "risk" if name == "Risk" else ""
        rows += (
            f'<div class="dna-row"><div class="dna-name">{name}</div>'
            f'<div class="dna-track"><div class="dna-fill {css}" '
            f'style="width:{score:.0f}%"></div></div>'
            f'<div class="dna-value">{score:.0f}</div></div>'
        )
    return (
        f'<div class="panel"><div class="dna-title">{title}</div>{rows}'
        f'<div class="dna-status">{label}</div></div>'
    )


def breakdown_html(breakdown: dict[str, float]) -> str:
    """Le sei componenti dell'Health Score come barre con colore di stato."""
    rows = ""
    for name, score in breakdown.items():
        if score != score:
            continue
        color = _status_color(score)
        rows += (
            f'<div class="dna-row"><div class="dna-name" style="width:110px">{name}'
            f'</div><div class="dna-track"><div class="dna-fill" '
            f'style="width:{score:.0f}%;background:{color}"></div></div>'
            f'<div class="dna-value" style="color:{color}">{score:.0f}</div></div>'
        )
    return (
        f'<div class="panel"><div class="dna-title">COME SI FORMA IL PUNTEGGIO</div>'
        f"{rows}</div>"
    )


LANDING_CSS = """
<style>
.landing-hero {
    position: relative; overflow: hidden;
    background:
        radial-gradient(900px 380px at 82% -10%, rgba(247,166,0,0.16), transparent 60%),
        radial-gradient(700px 300px at 8% 110%, rgba(57,135,229,0.12), transparent 60%),
        linear-gradient(165deg, #12161e 0%, #0c0f15 70%);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 22px;
    padding: 74px 60px 66px;
    text-align: center;
    animation: fadeUp .5s ease-out both;
}
.landing-title {
    font-family: 'Space Grotesk', 'Inter', sans-serif !important;
    font-size: 3rem; font-weight: 700; letter-spacing: -0.02em;
    line-height: 1.12; margin: 0 auto 16px; max-width: 720px; color: #f2f3f7;
}
.landing-title em { font-style: normal; color: #f7a600; }
.landing-sub {
    font-size: 1.08rem; color: #9aa2b1; max-width: 560px;
    margin: 0 auto 8px; line-height: 1.6;
}
.glass-row { display: flex; gap: 18px; margin-top: 22px; }
.glass {
    flex: 1; text-align: center;
    background: rgba(255,255,255,0.035);
    backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 16px; padding: 26px 18px;
    animation: fadeUp .6s ease-out both;
}
.glass:nth-child(2) { animation-delay: .12s; }
.glass:nth-child(3) { animation-delay: .24s; }
.glass-num {
    font-family: 'Space Grotesk', 'Inter', sans-serif !important;
    font-size: 2rem; font-weight: 700; color: #f7a600;
    font-variant-numeric: tabular-nums;
}
.glass-label {
    font-size: 0.78rem; color: #8b93a3; text-transform: uppercase;
    letter-spacing: 0.09em; font-weight: 600; margin-top: 4px;
}
@keyframes fadeUp {
    from { opacity: 0; transform: translateY(14px); }
    to { opacity: 1; transform: translateY(0); }
}
</style>
"""


def render_landing(on_start) -> None:
    """Landing page: hero, CTA, statistiche in glass card."""
    st.markdown(LANDING_CSS, unsafe_allow_html=True)
    st.markdown(
        """
        <div class="landing-hero">
          <div class="landing-title">Capisci il tuo portafoglio
          in <em>60 secondi</em>.</div>
          <div class="landing-sub">Health score, problemi concreti e rischio
          misurato in euro, cambio incluso. Onesto per costruzione:
          nessuna promessa di rendimento, solo i tuoi dati.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    col_left, col_cta, col_right = st.columns([1, 1.2, 1])
    with col_cta:
        st.button(
            "Analizza il mio portafoglio",
            type="primary",
            width="stretch",
            on_click=on_start,
        )
    st.markdown(
        """
        <div class="glass-row">
          <div class="glass"><div class="glass-num">60s</div>
            <div class="glass-label">al primo report</div></div>
          <div class="glass"><div class="glass-num">6</div>
            <div class="glass-label">componenti dell'health score</div></div>
          <div class="glass"><div class="glass-num">103</div>
            <div class="glass-label">titoli Nasdaq-100 coperti</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption(
        "Analisi in euro con rischio cambio EUR/USD incluso · report PDF "
        "condivisibile · nessuna registrazione richiesta. Non è consulenza "
        "finanziaria."
    )
