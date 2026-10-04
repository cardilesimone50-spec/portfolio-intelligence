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
.aw-header { text-align: center; padding: 28px 20px 4px; animation: fadeUp .5s ease-out both; }
.aw-eyebrow {
    display: inline-block; font-size: 0.72rem; font-weight: 700;
    letter-spacing: 0.14em; color: #1E40AF; background: #EEF2FF;
    border: 1px solid #C7D2FE; border-radius: 999px; padding: 4px 14px;
    margin-bottom: 14px;
}
.aw-title {
    font-family: var(--font-display) !important;
    font-size: 2rem; font-weight: 700; letter-spacing: -0.01em; color: #14171e;
    margin: 0 0 10px;
}
.aw-sub { font-size: 1rem; color: #5a6270; max-width: 620px; margin: 0 auto 20px; }
.aw-badges { display: flex; gap: 10px; justify-content: center; flex-wrap: wrap; margin-bottom: 32px; }
.aw-badge {
    font-size: 0.72rem; font-weight: 600; color: #334155; background: #F1F5F9;
    border: 1px solid #E2E8F0; border-radius: 999px; padding: 5px 13px;
}
.aw-feature { display: flex; gap: 12px; margin-bottom: 22px; }
.aw-feature-icon { font-size: 1.3rem; line-height: 1.4; }
.aw-feature-title { font-weight: 700; color: #14171e; font-size: 0.95rem; }
.aw-feature-desc { color: #5a6270; font-size: 0.86rem; line-height: 1.45; }
.aw-login-box {
    background: #ffffff; border: 1px solid #E2E8F0; border-radius: 16px;
    padding: 28px 26px; box-shadow: 0 1px 3px rgba(15,23,42,0.04); height: 100%;
}
.aw-login-title {
    font-family: var(--font-display) !important;
    font-weight: 700; font-size: 1.1rem; color: #14171e; margin-bottom: 14px;
}
.aw-kpi-row { display: flex; gap: 16px; margin: 20px 0 28px; flex-wrap: wrap; }
.aw-kpi {
    flex: 1; min-width: 160px; background: #ffffff; border: 1px solid #E2E8F0;
    border-radius: 14px; padding: 16px 18px;
}
.aw-kpi-num {
    font-family: var(--font-display) !important;
    font-size: 1.5rem; font-weight: 700; color: #1E40AF;
}
.aw-kpi-label {
    font-size: 0.74rem; color: #6b7280; text-transform: uppercase;
    letter-spacing: 0.06em; font-weight: 600; margin-top: 2px;
}
</style>
"""


def _trust_badges() -> str:
    return f"""
    <div class="aw-badges">
      <span class="aw-badge">🔐 {t("advisorw.badge_sso")}</span>
      <span class="aw-badge">🏢 {t("advisorw.badge_tenant")}</span>
      <span class="aw-badge">📋 {t("advisorw.badge_audit")}</span>
    </div>
    """


def _render_header() -> None:
    st.markdown(WELCOME_CSS, unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="aw-header">
          <div class="aw-eyebrow">{t("advisorw.eyebrow")}</div>
          <div class="aw-title">{t("advisorw.title")}</div>
          <div class="aw-sub">{t("advisorw.sub")}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(_trust_badges(), unsafe_allow_html=True)


def _continue_dev() -> None:
    st.session_state["advisor_welcome_dismissed"] = True


def _render_login_state() -> None:
    _render_header()
    col_features, col_login = st.columns([1.3, 1], gap="large")
    with col_features:
        for icon, title_key, desc_key in (
            ("📂", "advisorw.feature1_title", "advisorw.feature1_desc"),
            ("📊", "advisorw.feature2_title", "advisorw.feature2_desc"),
            ("📄", "advisorw.feature3_title", "advisorw.feature3_desc"),
        ):
            st.markdown(
                f"""
                <div class="aw-feature">
                  <div class="aw-feature-icon">{icon}</div>
                  <div>
                    <div class="aw-feature-title">{t(title_key)}</div>
                    <div class="aw-feature-desc">{t(desc_key)}</div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    with col_login:
        st.markdown(
            f'<div class="aw-login-box"><div class="aw-login-title">'
            f"{t('advisorw.login_title')}</div>",
            unsafe_allow_html=True,
        )
        if auth_configured():
            if st.button(t("advisorw.login_cta"), type="primary", width="stretch"):
                st.login()
        else:
            st.warning(t("advisorw.login_dev_warning"), icon="⚠️")
            if st.button(t("advisorw.login_dev_continue"), width="stretch"):
                _continue_dev()
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
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
