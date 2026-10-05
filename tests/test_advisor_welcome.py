"""Accesso all'area Advisor: la pagina di login, poi direttamente lo spazio di lavoro.

Stesso pattern bare-mode di test_tenant_isolation.py per admin.render():
st.stop() è un no-op fuori da `streamlit run`, quindi lo si monkeypatcha per
sollevare un'eccezione e verificare che il codice si sia fermato davvero —
non solo che non sia esploso.
"""

import pytest
import streamlit as st

from portfolio_intelligence.views import advisor_welcome as aw

ADVISOR = "mario@studio-example.it"


def _stop_raises(monkeypatch):
    def _stop():
        raise RuntimeError("st.stop() called")

    monkeypatch.setattr(aw.st, "stop", _stop)


def test_login_page_never_imports_the_portfolio_store():
    """Prima del login nessun dato di portafoglio: il modulo non usa store.py."""
    with open(aw.__file__) as f:
        assert "data.store" not in f.read()


def test_login_state_blocks_unauthenticated(monkeypatch):
    monkeypatch.setattr(aw, "is_authenticated", lambda: False)
    monkeypatch.setattr(aw, "auth_configured", lambda: False)
    st.session_state.pop("advisor_welcome_dismissed", None)
    _stop_raises(monkeypatch)

    with pytest.raises(RuntimeError, match="st.stop"):
        aw.render_advisor_gate(ADVISOR)


def test_login_state_shows_dev_warning_when_auth_not_configured(monkeypatch):
    """auth_configured() False: niente bottone SSO reale, solo l'avviso e
    l'uscita esplicita in dev — non deve mai crashare per client_id assente."""
    monkeypatch.setattr(aw, "is_authenticated", lambda: False)
    monkeypatch.setattr(aw, "auth_configured", lambda: False)
    st.session_state.pop("advisor_welcome_dismissed", None)
    _stop_raises(monkeypatch)

    with pytest.raises(RuntimeError):
        aw.render_advisor_gate(ADVISOR)  # non deve sollevare altro che lo stop


def test_authenticated_advisor_goes_straight_to_the_workspace(monkeypatch):
    monkeypatch.setattr(aw, "is_authenticated", lambda: True)
    st.session_state.pop("advisor_welcome_dismissed", None)
    _stop_raises(monkeypatch)

    aw.render_advisor_gate(ADVISOR)  # non deve fermarsi: nessuna schermata intermedia


def test_gate_passes_through_once_dismissed_even_if_not_authenticated(monkeypatch):
    """Dopo una quick action (o il 'continua in dev'), il gate non deve più
    bloccare nella stessa sessione — anche se is_authenticated() è ancora
    False (caso 'continua senza autenticazione')."""
    monkeypatch.setattr(aw, "is_authenticated", lambda: False)
    st.session_state["advisor_welcome_dismissed"] = True
    _stop_raises(monkeypatch)

    aw.render_advisor_gate(ADVISOR)  # non deve sollevare: passa oltre

    st.session_state.pop("advisor_welcome_dismissed", None)


def test_continue_dev_dismisses_the_gate():
    st.session_state.pop("advisor_welcome_dismissed", None)
    aw._continue_dev()
    assert st.session_state["advisor_welcome_dismissed"] is True
    st.session_state.pop("advisor_welcome_dismissed", None)
