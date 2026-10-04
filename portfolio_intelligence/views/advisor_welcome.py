"""Gate professionale di app_advisor.py: login istituzionale o welcome workspace.

Due stati, entrambi bloccanti (st.stop()) finché non si procede:
- Stato A (non autenticato): header enterprise, tre feature a sinistra, box
  di accesso SSO a destra. Se l'OIDC non è configurato (sviluppo), un avviso
  elegante sostituisce il bottone reale e offre un modo esplicito per
  continuare senza login — coerente con REQUIRE_AUTH, che di default non
  blocca l'uso locale (vedi portfolio_intelligence/ui/identity.py).
- Stato B (autenticato, prima volta nella sessione): saluto, KPI
  dell'advisor corrente, tre quick action che portano dentro la piattaforma.
  Una volta "dismissa" (via quick action), non si ripresenta nella sessione.

Non tocca gate.py (l'onboarding generico, condiviso con Investor): le quick
action impostano lo stage di gate.py e rifanno un rerun, poi è gate.py a
prendere il controllo normalmente.
"""

import streamlit as st

from portfolio_intelligence.data.store import last_date, list_portfolios, load_analyses
from portfolio_intelligence.i18n import t
from portfolio_intelligence.ui.identity import auth_configured, is_authenticated
from portfolio_intelligence.ui.legal import legal_footer
from portfolio_intelligence.views.common import SAMPLE_PORTFOLIO

WELCOME_CSS = """
<style>
.aw-header { padding: var(--s-6) 0 var(--s-5); max-width: 720px; }
.aw-title {
    font-family: var(--font-display) !important;
    font-size: 2.2rem; font-weight: 600; letter-spacing: -0.01em; color: var(--ink);
    line-height: 1.15; margin: 0 0 var(--s-3);
}
.aw-sub { font-size: 1.05rem; color: var(--muted); line-height: 1.6; margin: var(--s-3) 0 0; }
.aw-meta { font-size: 0.85rem; color: var(--ink-2); margin-top: var(--s-3); }
.aw-features { border-top: 1px solid var(--line); }
.aw-feature { padding: var(--s-4) 0; border-bottom: 1px solid var(--line); }
.aw-feature-title { font-weight: 600; color: var(--ink); font-size: 0.98rem; }
.aw-feature-desc {
    color: var(--muted); font-size: 0.9rem; line-height: 1.5; margin-top: var(--s-1);
}
.aw-login-title {
    font-family: var(--font-display) !important;
    font-weight: 600; font-size: 1.25rem; color: var(--ink); margin-bottom: var(--s-2);
}
.aw-kpi-row {
    display: flex; flex-wrap: wrap; margin: var(--s-4) 0 var(--s-5);
    background: var(--panel); border: 1px solid var(--line); border-radius: var(--r-lg);
}
.aw-kpi { flex: 1; min-width: 160px; padding: var(--s-4) var(--s-5); border-left: 1px solid var(--line); }
.aw-kpi:first-child { border-left: none; }
.aw-kpi-num {
    font-size: 1.5rem; font-weight: 700; color: var(--ink); font-variant-numeric: tabular-nums;
}
.aw-kpi-label {
    font-size: 0.75rem; color: var(--muted); text-transform: uppercase;
    letter-spacing: 0.06em; font-weight: 600; margin-top: var(--s-1);
}
</style>
"""


def _render_header() -> None:
    st.markdown(WELCOME_CSS, unsafe_allow_html=True)
    meta = " · ".join(
        t(key) for key in ("advisorw.badge_sso", "advisorw.badge_tenant", "advisorw.badge_audit")
    )
    st.markdown(
        '<div class="aw-header">'
        f'<h1 class="page-title aw-title">{t("advisorw.title")}</h1>'
        f'<div class="aw-sub">{t("advisorw.sub")}</div>'
        f'<div class="aw-meta">{meta}</div></div>',
        unsafe_allow_html=True,
    )


def _continue_dev() -> None:
    st.session_state["advisor_welcome_dismissed"] = True


def _render_login_state() -> None:
    _render_header()
    col_features, col_login = st.columns([1.3, 1], gap="large")
    with col_features:
        features = "".join(
            f'<div class="aw-feature"><div class="aw-feature-title">{t(f"advisorw.feature{i}_title")}'
            f'</div><div class="aw-feature-desc">{t(f"advisorw.feature{i}_desc")}</div></div>'
            for i in (1, 2, 3)
        )
        st.markdown(f'<div class="aw-features">{features}</div>', unsafe_allow_html=True)
    with col_login, st.container(border=True):
        st.markdown(
            f'<div class="aw-login-title">{t("advisorw.login_title")}</div>',
            unsafe_allow_html=True,
        )
        if auth_configured():
            if st.button(t("advisorw.login_cta"), type="primary", width="stretch"):
                st.login()
        else:
            st.warning(t("advisorw.login_dev_warning"))
            if st.button(t("advisorw.login_dev_continue"), width="stretch"):
                _continue_dev()
                st.rerun()
    legal_footer()
    st.stop()


def _go_load_portfolio() -> None:
    st.session_state["advisor_welcome_dismissed"] = True
    st.session_state.stage = "input"


def _go_clients() -> None:
    st.session_state["advisor_welcome_dismissed"] = True
    st.session_state.stage = "app"
    # la chiave della nav include la lingua corrente, e il suo valore deve
    # essere la label tradotta (non la chiave macro "Clients"): è quello
    # che st.segmented_control restituirebbe se l'utente l'avesse cliccata
    lang = st.session_state.get("language", "en")
    st.session_state[f"nav_{lang}"] = t("nav.clients")


def _go_stress_test() -> None:
    st.session_state["advisor_welcome_dismissed"] = True
    st.session_state.positions = {t_: dict(p) for t_, p in SAMPLE_PORTFOLIO.items()}
    st.session_state.stage = "app"


def _render_welcome_state(advisor: str) -> None:
    from portfolio_intelligence.data import yahoo_client

    _render_header()
    st.markdown(t("advisorw.welcome_greeting", advisor=advisor))

    n_portfolios = len(list_portfolios(advisor))
    history = load_analyses(advisor, limit=1)
    last_checkup = (
        str(history.iloc[0]["timestamp"])
        if not history.empty
        else t("advisorw.kpi_last_checkup_none")
    )
    feed_date = last_date()
    feed_label = str(feed_date.date()) if feed_date is not None else t("advisorw.kpi_feed_unknown")
    feed_source = yahoo_client.last_price_source

    st.markdown(
        f"""
        <div class="aw-kpi-row">
          <div class="aw-kpi"><div class="aw-kpi-num">{n_portfolios}</div>
            <div class="aw-kpi-label">{t("advisorw.kpi_portfolios")}</div></div>
          <div class="aw-kpi"><div class="aw-kpi-num">{last_checkup}</div>
            <div class="aw-kpi-label">{t("advisorw.kpi_last_checkup")}</div></div>
          <div class="aw-kpi"><div class="aw-kpi-num">{feed_label}</div>
            <div class="aw-kpi-label">{t("advisorw.kpi_feed")} · {feed_source}</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_a, col_b, col_c = st.columns(3, gap="medium")
    with col_a:
        st.button(
            t("advisorw.quick_load"), width="stretch", type="primary", on_click=_go_load_portfolio
        )
    with col_b:
        st.button(t("advisorw.quick_clients"), width="stretch", on_click=_go_clients)
    with col_c:
        st.button(t("advisorw.quick_stress"), width="stretch", on_click=_go_stress_test)

    legal_footer()
    st.stop()


def render_advisor_gate(advisor: str) -> None:
    """Punto d'ingresso: STATO A, STATO B, o pass-through se già superato."""
    if not is_authenticated() and not st.session_state.get("advisor_welcome_dismissed"):
        _render_login_state()
        return
    if not st.session_state.get("advisor_welcome_dismissed"):
        _render_welcome_state(advisor)
