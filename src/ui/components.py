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


def position_card_html(
    ticker: str, amount: float, weight: float, color: str, company: str = ""
) -> str:
    """Card compatta di una posizione. HTML flat: nessuna indentazione iniziale,
    altrimenti il markdown di Streamlit lo tratterebbe come blocco di codice."""
    name = f'<div class="pos-name">{company}</div>' if company else ""
    return (
        f'<div class="pos-row">'
        f'<div class="avatar" style="background:{color}">{ticker[:4]}</div>'
        f'<div class="pos-main">'
        f'<div class="pos-ticker">{ticker}<span class="pos-amt">· {eur(amount)}'
        f"</span></div>{name}"
        f'<div class="pos-weight-track"><div class="pos-weight-fill" '
        f'style="width:{weight:.0%};background:{color}"></div></div>'
        f'</div><div class="pos-pct">{weight:.0%}</div></div>'
    )


def ticker_preview_html(ticker: str, color: str, preview: dict | None) -> str:
    """Anteprima del titolo cercato (nome, settore, prezzo, variazione). HTML flat."""
    avatar = f'<div class="avatar" style="background:{color}">{ticker[:4]}</div>'
    if not preview:
        return (
            f'<div class="ticker-preview">{avatar}<div class="tp-main">'
            f'<div class="tp-name">{ticker}</div>'
            f'<div class="tp-meta">Titolo personalizzato</div></div></div>'
        )
    meta = ticker + (f" · {preview['sector']}" if preview.get("sector") else "")
    price_html = ""
    if preview.get("price") is not None:
        sym = "$" if preview.get("currency") == "USD" else preview.get("currency", "")
        chg = preview.get("change")
        chg_html = ""
        if chg is not None:
            css = "up" if chg >= 0 else "down"
            arrow = "▲" if chg >= 0 else "▼"
            chg_html = f'<span class="tp-chg {css}">{arrow} {chg:+.2f}%</span>'
        price_html = f'<div class="tp-price">{sym}{preview["price"]:,.2f} {chg_html}</div>'
    return (
        f'<div class="ticker-preview">{avatar}<div class="tp-main">'
        f'<div class="tp-name">{preview["name"]}</div>'
        f'<div class="tp-meta">{meta}</div>{price_html}</div></div>'
    )


def hero_html(
    health: int,
    value: str,
    change: float,
    period: str,
    today_move: float | None = None,
) -> str:
    gauge_color = _status_color(health)
    arrow, css = ("▲", "up") if change >= 0 else ("▼", "down")
    today_html = ""
    if today_move is not None and today_move == today_move:
        arrow_t, css_t = ("▲", "up") if today_move >= 0 else ("▼", "down")
        today_html = (
            f'<div class="chg {css_t}" style="font-size:.85rem;margin-top:2px">'
            f"Ultima seduta {arrow_t} {today_move:+.2%}</div>"
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
        f'<div class="panel"><div class="dna-title">COME SI FORMA IL PUNTEGGIO</div>{rows}</div>'
    )


_ICONS = {
    "wave": '<path d="M2 12h4l3-8 4 16 3-8h4" fill="none" stroke="currentColor" '
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>',
    "bolt": '<path d="M13 2 5 14h6l-1 8 8-12h-6l1-8z" fill="none" stroke="currentColor" '
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>',
    "down": '<path d="M3 7l7 7 4-4 7 7M21 17v-6h-6" fill="none" stroke="currentColor" '
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>',
    "search": '<circle cx="11" cy="11" r="7" fill="none" stroke="currentColor" '
    'stroke-width="2"/><path d="M21 21l-4.3-4.3" stroke="currentColor" '
    'stroke-width="2" stroke-linecap="round"/>',
    "folder": '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5'
    'a2 2 0 0 1-2-2z" fill="none" stroke="currentColor" stroke-width="2" '
    'stroke-linejoin="round"/>',
}


def _icon_svg(name: str) -> str:
    return (
        f'<svg viewBox="0 0 24 24" width="19" height="19" '
        f'xmlns="http://www.w3.org/2000/svg">{_ICONS[name]}</svg>'
    )


def kpi_row_html(cards: list[dict]) -> str:
    """Riga di KPI card con icona: [{icon, label, value, sub, color?}]."""
    html = '<div class="kpi-row">'
    for card in cards:
        color = card.get("color", AMBER)
        html += f"""
        <div class="kpi">
          <div class="kpi-top">
            <div class="kpi-label">{card["label"]}</div>
            <div class="kpi-icon" style="color:{color};
                 background:{color}1f">{_icon_svg(card["icon"])}</div>
          </div>
          <div class="kpi-value">{card["value"]}</div>
          <div class="kpi-sub">{card["sub"]}</div>
        </div>"""
    return html + "</div>"


DISCLAIMER = (
    "Strumento di sola informazione, non di consulenza finanziaria. "
    "Le analisi descrivono caratteristiche misurabili del portafoglio sulla "
    "base di dati storici e non costituiscono raccomandazioni personalizzate "
    "di investimento né previsioni. Nessuna sollecitazione all'acquisto o alla "
    "vendita di strumenti finanziari. Le decisioni restano dell'utente o del "
    "suo consulente."
)


def compliance_footer() -> None:
    """Informativa MiFID persistente, visibile in ogni schermata."""
    st.markdown(
        f'<div class="compliance">{DISCLAIMER}</div>',
        unsafe_allow_html=True,
    )


def empty_state(title: str, hint: str, icon: str = "search") -> None:
    """Stato vuoto elegante al posto del box info di default."""
    st.markdown(
        f"""
        <div class="empty">
          <div class="empty-icon">{_icon_svg(icon)}</div>
          <div class="empty-title">{title}</div>
          <div class="empty-hint">{hint}</div>
        </div>""",
        unsafe_allow_html=True,
    )


LANDING_CSS = """
<style>
.landing-hero {
    position: relative; overflow: hidden;
    background:
        radial-gradient(900px 380px at 82% -10%, rgba(181,116,0,0.10), transparent 60%),
        radial-gradient(700px 300px at 8% 110%, rgba(57,135,229,0.08), transparent 60%),
        linear-gradient(165deg, #ffffff 0%, #eef1f5 70%);
    border: 1px solid rgba(20,25,35,0.09);
    border-radius: 22px;
    padding: 74px 60px 66px;
    text-align: center;
    box-shadow: 0 8px 30px rgba(20,25,35,0.05);
    animation: fadeUp .5s ease-out both;
}
.landing-title {
    font-family: 'Space Grotesk', 'Inter', sans-serif !important;
    font-size: 3rem; font-weight: 700; letter-spacing: -0.02em;
    line-height: 1.12; margin: 0 auto 16px; max-width: 720px; color: #14171e;
}
.landing-title em { font-style: normal; color: #b57400; }
.landing-sub {
    font-size: 1.08rem; color: #5a6270; max-width: 560px;
    margin: 0 auto 8px; line-height: 1.6;
}
.glass-row { display: flex; gap: 18px; margin-top: 22px; }
.glass {
    flex: 1; text-align: center;
    background: #ffffff;
    border: 1px solid rgba(20,25,35,0.09);
    border-radius: 16px; padding: 26px 18px;
    box-shadow: 0 4px 14px rgba(20,25,35,0.04);
    animation: fadeUp .6s ease-out both;
}
.glass:nth-child(2) { animation-delay: .12s; }
.glass:nth-child(3) { animation-delay: .24s; }
.glass-num {
    font-family: 'Space Grotesk', 'Inter', sans-serif !important;
    font-size: 2rem; font-weight: 700; color: #b57400;
    font-variant-numeric: tabular-nums;
}
.glass-label {
    font-size: 0.78rem; color: #6b7280; text-transform: uppercase;
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
