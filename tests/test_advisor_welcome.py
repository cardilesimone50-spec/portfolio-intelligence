"""Gate professionale di app_advisor.py: login istituzionale e welcome workspace.

Stesso pattern bare-mode di test_tenant_isolation.py per admin.render():
st.stop() è un no-op fuori da `streamlit run`, quindi lo si monkeypatcha per
sollevare un'eccezione e verificare che il codice si sia fermato davvero —
non solo che non sia esploso.
"""

import pandas as pd
import pytest
import streamlit as st

from portfolio_intelligence.views import advisor_welcome as aw

ADVISOR = "mario@studio-example.it"


def _stop_raises(monkeypatch):
    def _stop():
        raise RuntimeError("st.stop() called")

    monkeypatch.setattr(aw.st, "stop", _stop)


def _boom(*_a, **_k):
    raise AssertionError("store.py function called when it should not have been")


def test_login_state_blocks_unauthenticated_without_touching_store(monkeypatch):
    monkeypatch.setattr(aw, "is_authenticated", lambda: False)
    monkeypatch.setattr(aw, "auth_configured", lambda: False)
    monkeypatch.setattr(aw, "list_portfolios", _boom)
    monkeypatch.setattr(aw, "load_analyses", _boom)
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


def test_welcome_state_shown_once_authenticated_and_reads_own_advisor_data(monkeypatch):
    calls = {"advisor_seen": None}

    def _fake_list_portfolios(advisor, **_k):
        calls["advisor_seen"] = advisor
        return {"Client A": {}, "Client B": {}}

    monkeypatch.setattr(aw, "is_authenticated", lambda: True)
    monkeypatch.setattr(aw, "list_portfolios", _fake_list_portfolios)
    monkeypatch.setattr(aw, "load_analyses", lambda *a, **k: pd.DataFrame())
    monkeypatch.setattr(aw, "last_date", lambda: None)
    st.session_state.pop("advisor_welcome_dismissed", None)
    _stop_raises(monkeypatch)

    with pytest.raises(RuntimeError, match="st.stop"):
        aw.render_advisor_gate(ADVISOR)

    assert calls["advisor_seen"] == ADVISOR  # mai un advisor diverso/fisso


def test_gate_passes_through_once_dismissed_even_if_not_authenticated(monkeypatch):
    """Dopo una quick action (o il 'continua in dev'), il gate non deve più
    bloccare nella stessa sessione — anche se is_authenticated() è ancora
    False (caso 'continua senza autenticazione')."""
    monkeypatch.setattr(aw, "is_authenticated", lambda: False)
    monkeypatch.setattr(aw, "list_portfolios", _boom)
    monkeypatch.setattr(aw, "load_analyses", _boom)
    st.session_state["advisor_welcome_dismissed"] = True
    _stop_raises(monkeypatch)

    aw.render_advisor_gate(ADVISOR)  # non deve sollevare: passa oltre

    st.session_state.pop("advisor_welcome_dismissed", None)


def test_continue_dev_dismisses_the_gate():
    st.session_state.pop("advisor_welcome_dismissed", None)
    aw._continue_dev()
    assert st.session_state["advisor_welcome_dismissed"] is True
    st.session_state.pop("advisor_welcome_dismissed", None)


def test_go_load_portfolio_sends_to_ticker_input():
    st.session_state.pop("advisor_welcome_dismissed", None)
    st.session_state.pop("stage", None)
    aw._go_load_portfolio()
    assert st.session_state["advisor_welcome_dismissed"] is True
    assert st.session_state.stage == "input"


def test_go_clients_selects_the_clients_tab_in_the_current_language():
    st.session_state.language = "en"
    st.session_state.pop("advisor_welcome_dismissed", None)
    aw._go_clients()
    assert st.session_state.stage == "app"
    assert st.session_state["nav_en"] == "Clients"  # label tradotta, non la chiave macro


def test_go_stress_test_loads_the_sample_portfolio():
    st.session_state.positions = {}
    st.session_state.pop("advisor_welcome_dismissed", None)
    aw._go_stress_test()
    assert st.session_state.stage == "app"
    assert set(st.session_state.positions) == {"AAPL", "MSFT", "NVDA"}
