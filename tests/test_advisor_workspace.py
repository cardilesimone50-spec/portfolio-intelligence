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


def _lots(ticker, qty=10.0):
    return {ticker: {"lots": [{"qty": qty, "price": 100.0, "date": "2025-01-02"}]}}


def _fake_analysis(health_by_ticker, calls=None):
    """Analisi finta: l'Health dipende dai titoli posseduti, nessuna rete."""

    def fake(items, _period, _in_eur, _lang="en"):
        if calls is not None:
            calls.append(dict(items))
        health = min((health_by_ticker.get(ticker, 70) for ticker, _ in items), default=70)
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
    save_portfolio(ADVISOR, "C-HEALTHY", _lots("AAPL"))
    save_portfolio(ADVISOR, "C-WEAK", _lots("NVDA"))
    save_portfolio("other@y", "C-OTHER", POSITIONS)
    monkeypatch.setattr(ws, "quick_client_analysis", _fake_analysis({"NVDA": 20}))

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


# ---------------------------------------------------- casi limite (record storici, stato, privacy)


def _section(at, section):
    at.session_state["adv_section"] = section
    return at.run()


def test_legacy_client_without_profile_opens_on_every_section(offline):
    from sqlalchemy import text

    from portfolio_intelligence.data.store import get_engine

    with get_engine().begin() as conn:
        conn.execute(
            text(
                "INSERT INTO portfolios (advisor, name, positions, updated, risk_profile) "
                "VALUES ('adv@x', 'LEGACY', '{\"AAPL\": 1000.0}', '2025-01-01', NULL)"
            )
        )

    at = AppTest.from_function(_workspace_app).run()
    at.button(key="adv_open_0").click().run()
    assert not at.exception
    assert at.session_state["adv_profile"] == "Not set"
    for section in ("positions", "analysis", "strategies", "overview"):
        assert not _section(at, section).exception, section


def test_duplicate_code_shows_the_error_message(offline):
    save_portfolio(ADVISOR, "C-0042", POSITIONS)
    at = AppTest.from_function(_workspace_app).run()
    at.button(key="advnav_new").click().run()
    at.text_input(key="adv_new_name").input("C-0042").run()

    assert any(e.value == t_in("en", "adv.code_exists") for e in at.error)
    assert _button(at, t_in("en", "adv.create")).disabled


def test_client_created_meanwhile_elsewhere_is_not_overwritten(offline):
    """Codice libero quando il form è stato aperto, preso da un'altra scheda prima del clic."""
    at = AppTest.from_function(_workspace_app).run()
    at.button(key="advnav_new").click().run()
    at.text_input(key="adv_new_name").input("C-9").run()
    at.selectbox(key="adv_new_profile").select("Aggressive").run()
    at.session_state["positions"] = _lots("MSFT")
    at.run()
    save_portfolio(ADVISOR, "C-9", POSITIONS, risk_profile="Conservative")  # l'altra scheda

    _button(at, t_in("en", "adv.create")).click().run()

    assert list_clients(ADVISOR)["C-9"]["risk_profile"] == "Conservative"
    assert any(e.value == t_in("en", "adv.code_exists") for e in at.error)
    assert at.session_state["adv_page"] == "new_client"


def test_risk_profile_belongs_to_one_client_only(offline):
    # volatilità finta 12%: sotto le soglie di entrambi i profili, quindi l'ordine è per codice
    save_portfolio(ADVISOR, "C-A", _lots("AAPL"), risk_profile="Aggressive")
    save_portfolio(ADVISOR, "C-B", _lots("MSFT"), risk_profile="Moderate")

    at = AppTest.from_function(_workspace_app).run()
    at.button(key="adv_open_0").click().run()
    assert at.session_state["adv_client"] == "C-A"
    _section(at, "positions")
    at.selectbox(key="adv_profile_sel_C-A").select("Conservative").run()
    assert at.session_state["adv_profile"] == "Conservative"

    at.button(key="advnav_clients").click().run()
    at.button(key="adv_open_1").click().run()
    assert at.session_state["adv_client"] == "C-B"
    assert at.session_state["adv_profile"] == "Moderate"  # nessun trascinamento da C-A
    _section(at, "positions")
    assert at.selectbox(key="adv_profile_sel_C-B").value == "Moderate"

    clients = list_clients(ADVISOR)
    assert clients["C-A"]["risk_profile"] == "Aggressive"  # la modifica non salvata non va su DB
    assert clients["C-B"]["risk_profile"] == "Moderate"

    at.button(key="advnav_clients").click().run()
    at.button(key="adv_open_0").click().run()
    assert at.session_state["adv_profile"] == "Conservative"  # la bozza di C-A è rimasta sua

    at.button(key="advnav_new").click().run()
    assert at.selectbox(key="adv_new_profile").value == "Not set"  # nessun default globale


def test_unsaved_changes_survive_navigation_and_can_be_discarded(offline):
    save_portfolio(ADVISOR, "C-A", {**_lots("AAPL"), **_lots("MSFT")}, risk_profile="Moderate")

    at = AppTest.from_function(_workspace_app).run()
    at.button(key="adv_open_0").click().run()
    _section(at, "positions")
    at.button(key="adv_del_MSFT").click().run()
    assert any(w.value == t_in("en", "adv.unsaved") for w in at.warning)

    at.button(key="advnav_clients").click().run()  # si esce senza salvare
    assert any("C-A" in w.value for w in at.warning)  # il book segnala la bozza
    assert set(list_clients(ADVISOR)["C-A"]["positions"]) == {"AAPL", "MSFT"}

    at.button(key="adv_open_0").click().run()  # la bozza torna
    assert set(at.session_state["positions"]) == {"AAPL"}

    at.button(key="adv_discard").click().run()
    assert set(at.session_state["positions"]) == {"AAPL", "MSFT"}
    assert not any(w.value == t_in("en", "adv.unsaved") for w in at.warning)


def test_saved_changes_reach_the_book_immediately(offline, monkeypatch):
    """Nessuna cache da svuotare a mano: l'analisi del book è indicizzata dalle
    posizioni, quindi dopo il salvataggio viene ricalcolata sulle nuove."""
    calls: list[dict] = []
    monkeypatch.setattr(ws, "quick_client_analysis", _fake_analysis({}, calls))
    save_portfolio(ADVISOR, "C-A", {**_lots("AAPL"), **_lots("MSFT")})

    at = AppTest.from_function(_workspace_app).run()
    at.button(key="adv_open_0").click().run()
    _section(at, "positions")
    at.button(key="adv_del_MSFT").click().run()
    _button(at, t_in("en", "adv.save")).click().run()
    calls.clear()
    at.button(key="advnav_clients").click().run()

    assert set(list_clients(ADVISOR)["C-A"]["positions"]) == {"AAPL"}
    assert [set(c) for c in calls] == [{"AAPL"}]


def test_report_heading_reaches_the_pdf_but_never_the_database(offline, monkeypatch):
    from sqlalchemy import MetaData, select

    from portfolio_intelligence.data.store import get_engine

    seen: list[str] = []
    monkeypatch.setattr(ws, "_client_analysis", lambda *a, **k: seen.append(a[-1]))
    save_portfolio(ADVISOR, "C-A", _lots("AAPL"))

    at = AppTest.from_function(_workspace_app).run()
    at.button(key="adv_open_0").click().run()
    at.text_input(key="adv_recipient_in_C-A").input("Mario Rossi").run()
    _section(at, "positions")
    at.button(key="adv_del_AAPL").click().run()
    _button(at, t_in("en", "adv.save")).click().run()  # anche un salvataggio non la porta su DB
    _section(at, "overview")

    assert seen[-1] == "Mario Rossi"
    engine = get_engine()
    meta = MetaData()
    meta.reflect(engine)
    with engine.connect() as conn:
        dump = " ".join(
            str(row) for table in meta.tables.values() for row in conn.execute(select(table))
        )
    assert "Mario Rossi" not in dump
