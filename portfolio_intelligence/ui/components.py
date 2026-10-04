"""Componenti UI riusabili: hero, card, sezioni, breakdown, landing."""

import streamlit as st

from portfolio_intelligence.config import HEALTH_SCORE_FAIR, HEALTH_SCORE_GOOD
from portfolio_intelligence.i18n import t
from portfolio_intelligence.visualization.charts import AMBER_TEXT, GAIN, GAIN_TEXT, LOSS

AMBER = "#d97706"  # status mid-band (gauge/health)


def _comp_name(name: str) -> str:
    """Nome componente tradotto; se non in catalogo, resta com'è."""
    translated = t(f"comp.{name}")
    return name if translated.startswith("comp.") else translated


def eur(value: float) -> str:
    return f"{value:,.0f} €".replace(",", ".")


def sec(title: str) -> None:
    """Etichetta di sezione con barretta ambra."""
    st.markdown(f'<div class="sec">{title}</div>', unsafe_allow_html=True)


def _status_color(score: float) -> str:
    return GAIN if score >= HEALTH_SCORE_GOOD else AMBER if score >= HEALTH_SCORE_FAIR else LOSS


def text_safe(color: str) -> str:
    """Variante del colore di stato leggibile come testo su bianco (WCAG AA)."""
    return {GAIN: GAIN_TEXT, AMBER: AMBER_TEXT}.get(color, color)


def _luminance(hex_color: str) -> float:
    channels = [int(hex_color.lstrip("#")[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    r, g, b = (c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def on_color(background: str) -> str:
    """Testo bianco o scuro sopra `background`: quello a contrasto più alto."""
    lum = _luminance(background)
    white_contrast = 1.05 / (lum + 0.05)
    ink_contrast = (lum + 0.05) / (_luminance("#0F172A") + 0.05)
    return "#ffffff" if white_contrast >= ink_contrast else "#0F172A"


def _avatar(ticker: str, color: str) -> str:
    return (
        f'<div class="avatar" aria-hidden="true" '
        f'style="background:{color};color:{on_color(color)}">{ticker[:4]}</div>'
    )


def position_card_html(
    ticker: str,
    amount: float,
    weight: float,
    color: str,
    company: str = "",
    amount_label: str | None = None,
    right_label: str | None = None,
) -> str:
    """Card compatta di una posizione. HTML flat: nessuna indentazione iniziale,
    altrimenti il markdown di Streamlit lo tratterebbe come blocco di codice.

    `amount_label` sostituisce la formattazione EUR (es. carico in USD);
    `right_label` sostituisce la percentuale a destra (es. P&L colorato).
    """
    name = f'<div class="pos-name">{company}</div>' if company else ""
    shown_amount = amount_label if amount_label is not None else eur(amount)
    right = right_label if right_label is not None else f"{weight:.0%}"
    return (
        f'<div class="pos-row">'
        f"{_avatar(ticker, color)}"
        f'<div class="pos-main">'
        f'<div class="pos-ticker">{ticker}<span class="pos-amt">· {shown_amount}'
        f"</span></div>{name}"
        f'<div class="pos-weight-track"><div class="pos-weight-fill" '
        f'style="width:{weight:.0%};background:{color}"></div></div>'
        f'</div><div class="pos-pct">{right}</div></div>'
    )


def ticker_preview_html(ticker: str, color: str, preview: dict | None) -> str:
    """Anteprima del titolo cercato (nome, settore, prezzo, variazione). HTML flat."""
    avatar = _avatar(ticker, color)
    if not preview:
        return (
            f'<div class="ticker-preview">{avatar}<div class="tp-main">'
            f'<div class="tp-name">{ticker}</div>'
            f'<div class="tp-meta">Custom ticker</div></div></div>'
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
    gain: float | None = None,
    gain_pct: float | None = None,
    irr: float | None = None,
) -> str:
    gauge_color = _status_color(health)
    arrow, css = ("▲", "up") if change >= 0 else ("▼", "down")
    gain_html = ""
    if gain is not None and gain == gain:
        css_g = "up" if gain >= 0 else "down"
        pct = f"{gain_pct:+.1%}" if gain_pct is not None and gain_pct == gain_pct else "—"
        irr_text = t("hero.irr", irr=f"{irr:+.1%}") if irr is not None and irr == irr else ""
        gain_html = (
            f'<div class="chg chg-line {css_g}">'
            f"{t('hero.gain_line', amount=eur(gain) if gain < 0 else '+' + eur(gain), pct=pct)}"
            f"{irr_text}</div>"
        )
    today_html = ""
    if today_move is not None and today_move == today_move:
        arrow_t, css_t = ("▲", "up") if today_move >= 0 else ("▼", "down")
        today_html = (
            f'<div class="chg chg-line small {css_t}">'
            f"{t('hero.last_session')} {arrow_t} {today_move:+.2%}</div>"
        )
    return f"""
    <div class="hero-panel" style="--val:{health}; --gcol:{gauge_color}">
      <div class="gauge"><div class="gauge-inner">
        <span class="gauge-num">{health}</span>
        <span class="gauge-sub">HEALTH /100</span>
      </div></div>
      <div class="hero-meta">
        <div class="label">{t("hero.value")}</div>
        <div class="big">{value}</div>
        <div class="chg {css}">{arrow} {change:+.1%} · {period}</div>
        {gain_html}
        {today_html}
      </div>
    </div>"""


def dna_card_html(dna: dict[str, float], label: str, title: str | None = None) -> str:
    title = title or t("hero.dna_title")
    rows = ""
    for name, score in dna.items():
        css = "risk" if name == "Risk" else ""
        known = score == score  # NaN: dato non disponibile, non zero
        rows += (
            f'<div class="dna-row"><div class="dna-name">{_comp_name(name)}</div>'
            f'<div class="dna-track"><div class="dna-fill {css}" '
            f'style="width:{score if known else 0:.0f}%"></div></div>'
            f'<div class="dna-value">{f"{score:.0f}" if known else "—"}</div></div>'
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
            f'<div class="dna-row"><div class="dna-name" style="width:110px">{_comp_name(name)}'
            f'</div><div class="dna-track"><div class="dna-fill" '
            f'style="width:{score:.0f}%;background:{color}"></div></div>'
            f'<div class="dna-value" style="color:{text_safe(color)}">{score:.0f}</div></div>'
        )
    return f'<div class="panel"><div class="dna-title">{t("hero.score_built")}</div>{rows}</div>'


def kpi_row_html(cards: list[dict]) -> str:
    """Striscia di KPI in un solo pannello: [{label, value, sub}]."""
    cells = "".join(
        f'<div class="kpi"><div class="kpi-label">{card["label"]}</div>'
        f'<div class="kpi-value">{card["value"]}</div>'
        f'<div class="kpi-sub">{card["sub"]}</div></div>'
        for card in cards
    )
    return f'<div class="kpi-row">{cells}</div>'


def compliance_footer() -> None:
    """Informativa MiFID persistente, visibile in ogni schermata."""
    from portfolio_intelligence.ui.legal import legal_footer

    st.markdown(
        f'<div class="compliance">{t("app.disclaimer")}</div>',
        unsafe_allow_html=True,
    )
    legal_footer()


def notice(text: str) -> None:
    """Avviso informativo neutro, senza icona né colore di stato."""
    st.markdown(f'<div class="notice">{text}</div>', unsafe_allow_html=True)


def empty_state(title: str, hint: str) -> None:
    """Stato vuoto: titolo e suggerimento, al posto del box info di default."""
    st.markdown(
        f'<div class="empty"><div class="empty-title">{title}</div>'
        f'<div class="empty-hint">{hint}</div></div>',
        unsafe_allow_html=True,
    )


LANDING_CSS = """
<style>
.landing-hero { padding: var(--s-7) 0 var(--s-5); }
.landing-side { padding-top: var(--s-7); }
.landing-title {
    font-family: var(--font-display) !important;
    font-size: 2.6rem; font-weight: 600; letter-spacing: -0.01em;
    line-height: 1.15; margin: 0 0 var(--s-4); color: var(--ink);
}
.landing-sub {
    font-size: 1.05rem; color: var(--muted); line-height: 1.6; max-width: 560px;
    margin-top: var(--s-4);
}
.landing-panel {
    background: var(--panel); border: 1px solid var(--line); border-radius: var(--r-lg);
    padding: var(--s-5) var(--s-5) var(--s-2);
}
.landing-panel-h {
    font-size: 0.75rem; font-weight: 600; letter-spacing: 0.08em;
    text-transform: uppercase; color: var(--muted); margin-bottom: var(--s-2);
}
.feat {
    display: flex; gap: var(--s-4); padding: var(--s-3) 0; border-top: 1px solid var(--line);
}
.landing-panel-h + .feat { border-top: none; }
.feat-ix {
    flex: none; width: 24px; font-size: 0.8rem; font-weight: 700;
    color: var(--muted); font-variant-numeric: tabular-nums; padding-top: 1px;
}
.feat-t { font-weight: 600; font-size: 0.95rem; color: var(--ink); }
.feat-d { font-size: 0.88rem; color: var(--muted); line-height: 1.5; margin-top: 2px; }
.landing-cta-note { font-size: 0.8rem; color: var(--muted); margin-top: var(--s-1); }
.facts {
    display: grid; grid-template-columns: repeat(3, 1fr);
    border-top: 1px solid var(--line); border-bottom: 1px solid var(--line);
    margin: var(--s-7) 0 var(--s-4);
}
.fact { padding: var(--s-5); border-left: 1px solid var(--line); }
.fact:first-child { border-left: none; padding-left: 0; }
.fact-n {
    font-size: 1.5rem; font-weight: 700; color: var(--ink); font-variant-numeric: tabular-nums;
}
.fact-l { font-size: 0.85rem; color: var(--muted); margin-top: 2px; }
.landing-legal { font-size: 0.8rem; color: var(--muted); }
@media (max-width: 900px) {
    .landing-hero { padding-top: var(--s-5); }
    .landing-side { padding-top: var(--s-3); }
    .landing-title { font-size: 2rem; }
    .facts { grid-template-columns: 1fr; }
    .fact { border-left: none; border-top: 1px solid var(--line); padding-left: 0; }
    .fact:first-child { border-top: none; }
}
</style>
"""


def render_landing(on_start) -> None:
    """Landing: proposta, contenuto del report, CTA e dati di copertura."""
    st.markdown(LANDING_CSS, unsafe_allow_html=True)
    features = "".join(
        f'<div class="feat"><div class="feat-ix">{i:02d}</div><div>'
        f'<div class="feat-t">{t(f"landing.f{i}_t")}</div>'
        f'<div class="feat-d">{t(f"landing.f{i}_d")}</div></div></div>'
        for i in range(1, 5)
    )
    left, right = st.columns([1.25, 1], gap="large")
    with left:
        st.markdown(
            '<div class="landing-hero">'
            f'<h1 class="page-title landing-title">{t("landing.title")}</h1>'
            f'<div class="landing-sub">{t("landing.sub")}</div></div>',
            unsafe_allow_html=True,
        )
        cta, _rest = st.columns([1, 1.4])
        with cta:
            st.button(t("landing.cta"), type="primary", width="stretch", on_click=on_start)
        st.markdown(
            f'<div class="landing-cta-note">{t("landing.cta_note")}</div>',
            unsafe_allow_html=True,
        )
    with right:
        st.markdown(
            '<div class="landing-side">'
            f'<div class="landing-panel"><div class="landing-panel-h">{t("landing.panel")}</div>'
            f"{features}</div></div>",
            unsafe_allow_html=True,
        )
    facts = "".join(
        f'<div class="fact"><div class="fact-n">{num}</div>'
        f'<div class="fact-l">{t(f"landing.fact{i}")}</div></div>'
        for i, num in enumerate(["103", "6", "EUR"], start=1)
    )
    st.markdown(
        f'<div class="facts">{facts}</div><div class="landing-legal">{t("landing.legal")}</div>',
        unsafe_allow_html=True,
    )


CHOOSER_CSS = """
<style>
.chooser-hero { padding: var(--s-7) 0 var(--s-6); max-width: 680px; }
.chooser-title {
    font-family: var(--font-display) !important;
    font-size: 2.4rem; font-weight: 600; letter-spacing: -0.01em;
    line-height: 1.15; margin: 0 0 var(--s-3); color: var(--ink);
}
.chooser-sub { font-size: 1.05rem; color: var(--muted); line-height: 1.6; margin: var(--s-3) 0 0; }
.profile-card {
    background: var(--panel); border: 1px solid var(--line); border-radius: var(--r-lg);
    padding: var(--s-5); margin-bottom: var(--s-3); min-height: 172px;
    display: flex; flex-direction: column; gap: var(--s-2);
}
.profile-card-title {
    font-family: var(--font-display) !important;
    font-size: 1.4rem; font-weight: 600; color: var(--ink);
}
.profile-card-desc { font-size: 0.95rem; color: var(--muted); line-height: 1.55; }
.chooser-footer { color: var(--muted); font-size: 0.88rem; margin-top: var(--s-5); }
</style>
"""


def render_profile_chooser(on_investor, on_advisor) -> None:
    """Prima schermata pubblica: scegli Investor (senza account) o Advisor (login).

    Due card affiancate; i bottoni sono widget nativi (non si può mettere un
    st.button dentro HTML arbitrario) renderizzati subito sotto ciascuna card.
    """
    st.markdown(CHOOSER_CSS, unsafe_allow_html=True)
    st.markdown(
        '<div class="chooser-hero">'
        f'<h1 class="page-title chooser-title">{t("chooser.title")}</h1>'
        f'<div class="chooser-sub">{t("chooser.sub")}</div></div>',
        unsafe_allow_html=True,
    )

    col_investor, col_advisor = st.columns(2, gap="large")
    for col, profile, on_click in (
        (col_investor, "investor", on_investor),
        (col_advisor, "advisor", on_advisor),
    ):
        with col:
            st.markdown(
                f'<div class="profile-card">'
                f'<div class="profile-card-title">{t(f"chooser.{profile}_title")}</div>'
                f'<div class="profile-card-desc">{t(f"chooser.{profile}_desc")}</div></div>',
                unsafe_allow_html=True,
            )
            st.button(
                t(f"chooser.{profile}_cta"),
                key=f"chooser_{profile}",
                type="primary" if profile == "investor" else "secondary",
                width="stretch",
                on_click=on_click,
            )

    st.markdown(
        f'<div class="chooser-footer">{t("chooser.footer")}</div>',
        unsafe_allow_html=True,
    )
