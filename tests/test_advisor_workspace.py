"""Spazio di lavoro Advisor: book clienti, nuovo cliente, cancellazioni (AppTest, senza rete)."""

import pytest
from streamlit.testing.v1 import AppTest

from portfolio_intelligence.data.store import list_clients, save_portfolio
from portfolio_intelligence.i18n import t_in
from portfolio_intelligence.views import advisor_workspace as ws
from portfolio_intelligence.views import sidebar

ADVISOR = "adv@x"
POSITIONS = {"AAPL": {"lots": [{"qty": 10.0, "price": 150.0, "date": "2025-01-02"}]}}


def _workspace_app():
    from portfolio_intelligence.views import advisor_workspace

    advisor_workspace.render("adv@x")


def _fake_analysis(health_by_client):
    def fake(items, _period, _in_eur, _lang="en"):
        ticker = dict(items).get("__client__")
        health = health_by_client.get(ticker, 70)
        return {
            "health": health,
            "value": 1000.0,
            "invested": 900.0,
            "cum": 0.1,
            "pnl_pct": 0.11,
            "vol": 0.12,
            "problem": "finding",
        }

    return fake


@pytest.fixture
def offline(tmp_path, monkeypatch):
    """DB temporaneo, nessuna rete: analisi e tasso privo di rischio finti."""
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'ws.db'}")
    monkeypatch.setattr(sidebar, "cached_risk_free", lambda: 0.03)
    monkeypatch.setattr(ws, "_client_analysis", lambda *a, **k: None)
    monkeypatch.setattr(ws, "quick_client_analysis", _fake_analysis({}))


def _button(at, label):
    return next(b for b in at.button if b.label == label)


def test_book_lists_only_own_clients_and_puts_the_one_to_review_first(offline, monkeypatch):
    # il tag "__client__" nelle posizioni finte permette di dare a ogni cliente il suo Health
    save_portfolio(ADVISOR, "C-HEALTHY", {**POSITIONS, "__client__": "C-HEALTHY"})
    save_portfolio(ADVISOR, "C-WEAK", {**POSITIONS, "__client__": "C-WEAK"})
    save_portfolio("other@y", "C-OTHER", POSITIONS)
    monkeypatch.setattr(ws, "quick_client_analysis", _fake_analysis({"C-WEAK": 20}))

    at = AppTest.from_function(_workspace_app).run()
    at.button(key="adv_open_0").click().run()

    assert at.session_state["adv_client"] == "C-WEAK"  # Health 20: da rivedere, in cima
    assert "C-OTHER" not in str(at.markdown)  # mai i clienti di un altro consulente


def test_new_client_is_saved_with_its_declared_risk_profile(offline):
    at = AppTest.from_function(_workspace_app).run()
    at.button(key="advnav_new").click().run()
    at.text_input(key="adv_new_name").input("C-0042")
    at.selectbox(key="adv_new_profile").select("Moderate")
    at.session_state["positions"] = POSITIONS
    at.run()
    _button(at, t_in("en", "adv.create")).click().run()

    clients = list_clients(ADVISOR)
    assert clients["C-0042"]["risk_profile"] == "Moderate"
    assert at.session_state["adv_page"] == "client"
    assert at.session_state["adv_client"] == "C-0042"


def test_cannot_create_a_client_twice_with_the_same_code(offline):
    save_portfolio(ADVISOR, "C-0042", POSITIONS, risk_profile="Aggressive")
    at = AppTest.from_function(_workspace_app).run()
    at.button(key="advnav_new").click().run()
    at.text_input(key="adv_new_name").input("C-0042")
    at.session_state["positions"] = {"MSFT": 10.0}
    at.run()

    assert _button(at, t_in("en", "adv.create")).disabled
    assert list_clients(ADVISOR)["C-0042"]["risk_profile"] == "Aggressive"  # non sovrascritto


def test_deleting_a_client_requires_explicit_confirmation(offline):
    """Art. 17 GDPR: si cancella dalla scheda cliente, solo dopo la conferma."""
    save_portfolio(ADVISOR, "C-A", POSITIONS)
    save_portfolio(ADVISOR, "C-B", POSITIONS)

    at = AppTest.from_function(_workspace_app).run()
    at.button(key="adv_open_0").click().run()
    opened = at.session_state["adv_client"]
    at.session_state["adv_section"] = "positions"
    at.run()
    assert at.button(key="adv_delete").disabled

    at.checkbox(key="del_confirm").check().run()
    at.button(key="adv_delete").click().run()

    remaining = set(list_clients(ADVISOR))
    assert remaining == {"C-A", "C-B"} - {opened}
    assert at.session_state["adv_page"] == "clients"


def test_erase_all_removes_only_the_current_advisor_data(offline):
    save_portfolio(ADVISOR, "C-A", POSITIONS)
    save_portfolio("other@y", "C-Z", POSITIONS)

    at = AppTest.from_function(_workspace_app).run()
    at.checkbox(key="erase_all_confirm").check().run()
    _button(at, t_in("en", "side.erase_all_btn")).click().run()

    assert list_clients(ADVISOR) == {}
    assert set(list_clients("other@y")) == {"C-Z"}


def test_workspace_never_shows_admin_to_non_admins(offline, monkeypatch):
    monkeypatch.setattr(ws, "is_admin", lambda _advisor: False)
    at = AppTest.from_function(_workspace_app)
    at.session_state["adv_page"] = "admin"
    at.run()

    assert at.session_state["adv_page"] == "clients"
    assert not any(b.key == "advnav_admin" for b in at.button)
