"""Accesso all'area Advisor: la pagina di login istituzionale.

Bloccante (st.stop()) finché il consulente non è autenticato. Se l'OIDC non è
configurato (sviluppo), un avviso sostituisce il bottone reale e offre un modo
esplicito per continuare senza login, coerente con REQUIRE_AUTH, che di
default non blocca l'uso locale (vedi portfolio_intelligence/ui/identity.py).
Dopo l'accesso si entra direttamente nello spazio di lavoro (book clienti).
"""

import streamlit as st

from portfolio_intelligence.i18n import t
from portfolio_intelligence.ui.area_switch import area_switch
from portfolio_intelligence.ui.identity import auth_configured, is_authenticated
from portfolio_intelligence.ui.legal import legal_footer

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
    _spacer, area_col = st.columns([4.6, 1.4])
    with area_col:
        area_switch("advisor", "area_sw_login")
    _render_header()
    col_features, col_login = st.columns([1.3, 1], gap="large")
    with col_features:
        features = "".join(
            f'<div class="aw-feature"><div class="aw-feature-title">{t(f"advisorw.feature{i}_title")}'
            f'</div><div class="aw-feature-desc">{t(f"advisorw.feature{i}_desc")}</div></div>'
            for i in (1, 2, 3, 4)
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


def render_advisor_gate(advisor: str) -> None:
    """Login se serve; altrimenti passa allo spazio di lavoro."""
    if not is_authenticated() and not st.session_state.get("advisor_welcome_dismissed"):
        _render_login_state()
