"""Componenti UI riusabili: hero, card, sezioni, breakdown, landing."""

import streamlit as st

from portfolio_intelligence.config import HEALTH_SCORE_FAIR, HEALTH_SCORE_GOOD
from portfolio_intelligence.i18n import t
from portfolio_intelligence.visualization.charts import GAIN, LOSS

AMBER = "#d97706"  # status mid-band (gauge/health)
ACCENT = "#1E40AF"  # brand primary


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
        f'<div class="avatar" style="background:{color}">{ticker[:4]}</div>'
        f'<div class="pos-main">'
        f'<div class="pos-ticker">{ticker}<span class="pos-amt">· {shown_amount}'
        f"</span></div>{name}"
        f'<div class="pos-weight-track"><div class="pos-weight-fill" '
        f'style="width:{weight:.0%};background:{color}"></div></div>'
        f'</div><div class="pos-pct">{right}</div></div>'
    )


def ticker_preview_html(ticker: str, color: str, preview: dict | None) -> str:
    """Anteprima del titolo cercato (nome, settore, prezzo, variazione). HTML flat."""
    avatar = f'<div class="avatar" style="background:{color}">{ticker[:4]}</div>'
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
            f'<div class="chg {css_g}" style="font-size:.95rem;margin-top:2px">'
            f"{t('hero.gain_line', amount=eur(gain) if gain < 0 else '+' + eur(gain), pct=pct)}"
            f"{irr_text}</div>"
        )
    today_html = ""
    if today_move is not None and today_move == today_move:
        arrow_t, css_t = ("▲", "up") if today_move >= 0 else ("▼", "down")
        today_html = (
            f'<div class="chg {css_t}" style="font-size:.85rem;margin-top:2px">'
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
            f'<div class="dna-value" style="color:{color}">{score:.0f}</div></div>'
        )
    return f'<div class="panel"><div class="dna-title">{t("hero.score_built")}</div>{rows}</div>'


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
        color = card.get("color", ACCENT)
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


def compliance_footer() -> None:
    """Informativa MiFID persistente, visibile in ogni schermata."""
    st.markdown(
        f'<div class="compliance">{t("app.disclaimer")}</div>',
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
.landing-hero { padding: 44px 0 22px; animation: fadeUp .4s ease-out both; }
.landing-side { padding-top: 44px; animation: fadeUp .5s ease-out both; }
.landing-eyebrow {
    font-size: 0.72rem; font-weight: 600; letter-spacing: 0.12em;
    text-transform: uppercase; color: var(--accent); margin-bottom: 14px;
}
.landing-title {
    font-family: var(--font-display) !important;
    font-size: 2.6rem; font-weight: 600; letter-spacing: -0.02em;
    line-height: 1.12; margin: 0 0 18px; color: var(--ink);
}
.landing-sub { font-size: 1.02rem; color: var(--muted); line-height: 1.65; max-width: 560px; }
.landing-panel {
    background: #fff; border: 1px solid var(--line); border-radius: 12px;
    padding: 22px 24px 8px;
    box-shadow: 0 1px 2px rgba(15,23,42,0.04), 0 8px 24px rgba(15,23,42,0.04);
}
.landing-panel-h {
    font-size: 0.68rem; font-weight: 600; letter-spacing: 0.08em;
    text-transform: uppercase; color: var(--muted); margin-bottom: 6px;
}
.feat { display: flex; gap: 14px; padding: 13px 0; border-top: 1px solid var(--line); }
.landing-panel-h + .feat { border-top: none; }
.feat-ix {
    flex: none; width: 24px; font-size: 0.75rem; font-weight: 700;
    color: var(--accent); font-variant-numeric: tabular-nums; padding-top: 1px;
}
.feat-t { font-weight: 600; font-size: 0.92rem; color: var(--ink); }
.feat-d { font-size: 0.84rem; color: var(--muted); line-height: 1.5; margin-top: 2px; }
.landing-cta-note { font-size: 0.8rem; color: var(--muted); margin-top: 2px; }
.facts {
    display: grid; grid-template-columns: repeat(3, 1fr);
    border-top: 1px solid var(--line); border-bottom: 1px solid var(--line);
    margin: 40px 0 14px;
}
.fact { padding: 20px 24px; border-left: 1px solid var(--line); }
.fact:first-child { border-left: none; padding-left: 0; }
.fact-n {
    font-family: var(--font-display) !important; font-size: 1.5rem; font-weight: 600;
    color: var(--ink); font-variant-numeric: tabular-nums;
}
.fact-l { font-size: 0.82rem; color: var(--muted); margin-top: 2px; }
.landing-legal { font-size: 0.76rem; color: var(--muted); }
@media (max-width: 900px) {
    .landing-hero { padding-top: 20px; }
    .landing-side { padding-top: 12px; }
    .landing-title { font-size: 2rem; }
    .facts { grid-template-columns: 1fr; }
    .fact { border-left: none; border-top: 1px solid var(--line); padding-left: 0; }
    .fact:first-child { border-top: none; }
}
@keyframes fadeUp {
    from { opacity: 0; transform: translateY(14px); }
    to { opacity: 1; transform: translateY(0); }
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
            f'<div class="landing-eyebrow">{t("landing.eyebrow")}</div>'
            f'<div class="landing-title">{t("landing.title")}</div>'
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
.chooser-hero {
    text-align: center; padding: 56px 20px 8px; animation: fadeUp .5s ease-out both;
}
.chooser-eyebrow {
    display: inline-block; font-size: 0.72rem; font-weight: 700;
    letter-spacing: 0.16em; color: #1E40AF; background: #EEF2FF;
    border: 1px solid #C7D2FE; border-radius: 999px; padding: 4px 14px;
    margin-bottom: 18px;
}
.chooser-title {
    font-family: 'Space Grotesk', 'Inter', sans-serif !important;
    font-size: 2.4rem; font-weight: 700; letter-spacing: -0.02em;
    line-height: 1.15; margin: 0 auto 12px; max-width: 640px; color: #14171e;
}
.chooser-sub { font-size: 1.04rem; color: #5a6270; margin: 0 auto 36px; }
.profile-card {
    height: 100%; background: #ffffff; border: 1px solid #E2E8F0;
    border-radius: 16px; padding: 30px 28px 22px;
    box-shadow: 0 1px 3px rgba(15,23,42,0.04);
    animation: fadeUp .6s ease-out both;
    display: flex; flex-direction: column; gap: 10px;
}
.profile-card.advisor { animation-delay: .1s; }
.profile-card-badge {
    font-size: 0.68rem; font-weight: 700; letter-spacing: 0.12em;
    text-transform: uppercase; color: #94a3b8;
}
.profile-card-title {
    font-family: 'Space Grotesk', 'Inter', sans-serif !important;
    font-size: 1.4rem; font-weight: 700; color: #14171e;
}
.profile-card-desc { font-size: 0.92rem; color: #5a6270; line-height: 1.55; flex: 1; }
.chooser-footer {
    text-align: center; color: #94a3b8; font-size: 0.85rem; margin-top: 28px;
}
</style>
"""


def render_profile_chooser(on_investor, on_advisor) -> None:
    """Prima schermata pubblica: scegli Investor (anonimo) o Advisor (login).

    Due card affiancate, stesso linguaggio visivo di `render_landing`. I
    bottoni sono widget nativi (non si può mettere un st.button dentro HTML
    arbitrario) renderizzati subito sotto ciascuna card — stesso pattern già
    usato da `render_landing` per il CTA principale.
    """
    st.markdown(CHOOSER_CSS, unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="chooser-hero">
          <div class="chooser-eyebrow">{t("chooser.eyebrow")}</div>
          <div class="chooser-title">{t("chooser.title")}</div>
          <div class="chooser-sub">{t("chooser.sub")}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_investor, col_advisor = st.columns(2, gap="large")
    with col_investor:
        st.markdown(
            f"""
            <div class="profile-card investor">
              <div class="profile-card-badge">{t("chooser.investor_badge")}</div>
              <div class="profile-card-title">{t("chooser.investor_title")}</div>
              <div class="profile-card-desc">{t("chooser.investor_desc")}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.button(
            t("chooser.investor_cta"),
            key="chooser_investor",
            type="primary",
            width="stretch",
            on_click=on_investor,
        )
    with col_advisor:
        st.markdown(
            f"""
            <div class="profile-card advisor">
              <div class="profile-card-badge">{t("chooser.advisor_badge")}</div>
              <div class="profile-card-title">{t("chooser.advisor_title")}</div>
              <div class="profile-card-desc">{t("chooser.advisor_desc")}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.button(
            t("chooser.advisor_cta"),
            key="chooser_advisor",
            width="stretch",
            on_click=on_advisor,
        )

    st.markdown(
        f'<div class="chooser-footer">{t("chooser.footer")}</div>',
        unsafe_allow_html=True,
    )
