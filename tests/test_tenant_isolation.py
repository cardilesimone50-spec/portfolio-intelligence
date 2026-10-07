"""Isolamento multi-tenant: gate REQUIRE_AUTH, confini advisor nel DB, vista Admin.

Copre ROADMAP.md §7 "Isolamento multi-tenant". Nessuna chiamata di rete: solo
SQLite su file temporaneo e mock di `streamlit.secrets`/`streamlit.stop`.
"""

import pandas as pd
import pytest

from portfolio_intelligence.data.store import (
    delete_portfolio,
    get_engine,
    list_portfolios,
    load_analyses,
    log_analysis,
    platform_stats,
    save_portfolio,
)
from portfolio_intelligence.ui import identity
from portfolio_intelligence.views import admin as admin_view
from portfolio_intelligence.views.context import ViewContext

ADVISOR_A = "advisor_a@example.com"
ADVISOR_B = "advisor_b@example.com"


def _engine(tmp_path):
    return get_engine(f"sqlite:///{tmp_path / 'isolation.db'}")


def _ctx(advisor: str) -> ViewContext:
    return ViewContext(
        computed=None,
        amounts={},
        total=0.0,
        portfolio=[],
        portfolio_name="My portfolio",
        period="1y",
        in_eur=True,
        risk_free=0.0,
        risk_profile="Not set",
        advisor=advisor,
    )


# ---------------------------------------------------------- (a) gate REQUIRE_AUTH


def test_require_auth_blocks_startup_without_oidc(monkeypatch):
    monkeypatch.setattr(identity, "auth_configured", lambda: False)
    monkeypatch.setenv("REQUIRE_AUTH", "true")
    assert identity.auth_required_but_missing() is True


def test_require_auth_does_not_block_when_oidc_configured(monkeypatch):
    monkeypatch.setattr(identity, "auth_configured", lambda: True)
    monkeypatch.setenv("REQUIRE_AUTH", "true")
    assert identity.auth_required_but_missing() is False


def test_require_auth_off_never_blocks(monkeypatch):
    monkeypatch.setattr(identity, "auth_configured", lambda: False)
    monkeypatch.setenv("REQUIRE_AUTH", "false")
    assert identity.auth_required_but_missing() is False


def test_require_auth_check_runs_inside_bootstrap_before_anything_else():
    """Regressione strutturale: auth_required_but_missing() deve stare,
    nel sorgente di router.bootstrap_page, PRIMA di qualunque rendering —
    non basta che la funzione esista, deve essere chiamata per prima."""
    with open("portfolio_intelligence/router.py") as f:
        source = f.read()
    def_pos = source.index("def bootstrap_page(")
    gate_pos = source.index("auth_required_but_missing(require_auth)", def_pos)
    # dopo il gate, bootstrap_page non fa più nient'altro che st.stop()
    next_def_pos = source.index("\ndef ", gate_pos)
    assert def_pos < gate_pos < next_def_pos


@pytest.mark.parametrize(
    ("entry_point", "ordered_calls"),
    [
        ("app_investor.py", ["bootstrap_page(", "gate.render_gate()", "render_sidebar("]),
        (
            "app_advisor.py",
            ["bootstrap_page(", "render_advisor_gate(", "advisor_workspace.render("],
        ),
    ],
)
def test_entry_points_bootstrap_before_gate_before_data(entry_point, ordered_calls):
    """Regressione strutturale: ciascun entry point chiama bootstrap_page()
    (che include il gate REQUIRE_AUTH), poi il proprio gate (onboarding o
    login), e solo dopo la UI che mostra dati: l'ordine conta, non solo la
    presenza."""
    with open(entry_point) as f:
        source = f.read()
    positions = [source.index(call) for call in ordered_calls]
    assert positions == sorted(positions)


# ---------------------------------------------------- (b)/(c) isolamento advisor


def test_advisor_sees_and_saves_only_its_own_portfolios(tmp_path):
    engine = _engine(tmp_path)
    save_portfolio(ADVISOR_A, "Client A1", {"AAPL": 100.0}, engine=engine)
    save_portfolio(ADVISOR_B, "Client B1", {"MSFT": 200.0}, engine=engine)

    book_a = list_portfolios(ADVISOR_A, engine=engine)
    book_b = list_portfolios(ADVISOR_B, engine=engine)

    assert set(book_a) == {"Client A1"}
    assert set(book_b) == {"Client B1"}


def test_advisor_b_cannot_overwrite_advisor_a_portfolio_with_same_name(tmp_path):
    engine = _engine(tmp_path)
    save_portfolio(ADVISOR_A, "Shared Name", {"AAPL": 100.0}, engine=engine)
    # B salva un portafoglio con lo STESSO nome: non deve toccare quello di A
    # (la chiave è composta (advisor, name), non solo name)
    save_portfolio(ADVISOR_B, "Shared Name", {"MSFT": 999.0}, engine=engine)

    book_a = list_portfolios(ADVISOR_A, engine=engine)
    book_b = list_portfolios(ADVISOR_B, engine=engine)

    assert book_a["Shared Name"] == {"AAPL": 100.0}
    assert book_b["Shared Name"] == {"MSFT": 999.0}


def test_advisor_b_cannot_delete_advisor_a_portfolio_by_name(tmp_path):
    engine = _engine(tmp_path)
    save_portfolio(ADVISOR_A, "Client A1", {"AAPL": 100.0}, engine=engine)

    # B prova a cancellare un portafoglio con lo stesso nome di A: la DELETE
    # è scoped su (advisor=B, name="Client A1") — nessuna riga corrisponde,
    # quello di A resta intatto. Nessuna eccezione: no-op silenzioso su dati
    # che non esistono per B, com'è corretto per una DELETE scoped.
    delete_portfolio(ADVISOR_B, "Client A1", engine=engine)

    assert list_portfolios(ADVISOR_A, engine=engine) == {"Client A1": {"AAPL": 100.0}}


def test_advisor_b_list_portfolios_never_returns_advisor_a_data(tmp_path):
    engine = _engine(tmp_path)
    save_portfolio(ADVISOR_A, "Secret Client", {"NVDA": 42.0}, engine=engine)

    # B non ha portafogli propri: il suo book è vuoto, non un errore e non
    # (per sbaglio) il book di A — niente data leak via fallback/default.
    assert list_portfolios(ADVISOR_B, engine=engine) == {}


def test_analyses_history_isolated_per_advisor(tmp_path):
    engine = _engine(tmp_path)
    log_analysis(
        ADVISOR_A,
        "Client A1",
        "1y",
        invested=1000.0,
        cum_return=0.1,
        risk_score=50,
        health=70,
        engine=engine,
    )

    history_a = load_analyses(ADVISOR_A, engine=engine)
    history_b = load_analyses(ADVISOR_B, engine=engine)

    assert len(history_a) == 1
    assert history_b.empty


# ------------------------------------------------------------- (d) vista Admin


def test_is_admin_true_only_for_allowlisted_email(monkeypatch):
    monkeypatch.setattr(identity.st, "secrets", {"admin_emails": [ADVISOR_A]})
    assert identity.is_admin(ADVISOR_A) is True
    assert identity.is_admin(ADVISOR_B) is False


def test_is_admin_case_insensitive(monkeypatch):
    monkeypatch.setattr(identity.st, "secrets", {"admin_emails": ["Admin@Example.com"]})
    assert identity.is_admin("admin@example.com") is True


def test_admin_view_blocks_non_admin_before_touching_cross_tenant_data(monkeypatch):
    calls = {"stats": False, "audit": False}
    monkeypatch.setattr(admin_view, "is_admin", lambda advisor: False)
    monkeypatch.setattr(
        admin_view, "platform_stats", lambda *a, **k: calls.__setitem__("stats", True)
    )
    monkeypatch.setattr(
        admin_view,
        "recent_audit",
        lambda *a, **k: calls.__setitem__("audit", True) or pd.DataFrame(),
    )

    def _stop():
        raise RuntimeError("st.stop() called")

    monkeypatch.setattr(admin_view.st, "stop", _stop)

    with pytest.raises(RuntimeError, match="st.stop"):
        admin_view.render(_ctx(ADVISOR_B))

    # il blocco deve avvenire PRIMA di qualunque lettura cross-tenant
    assert calls == {"stats": False, "audit": False}


def test_admin_view_renders_for_allowlisted_admin(monkeypatch, tmp_path):
    engine = _engine(tmp_path)
    save_portfolio(ADVISOR_A, "Client A1", {"AAPL": 100.0}, engine=engine)

    monkeypatch.setattr(admin_view, "is_admin", lambda advisor: True)
    monkeypatch.setattr(admin_view, "auth_configured", lambda: True)
    monkeypatch.setattr(
        admin_view, "platform_stats", lambda *a, **k: platform_stats(engine=engine)
    )
    monkeypatch.setattr(admin_view, "recent_audit", lambda *a, **k: pd.DataFrame())

    # non deve sollevare: l'admin passa il gate e la vista renderizza
    admin_view.render(_ctx(ADVISOR_A))


# ------------------------------------------- area Investor: nessuna tabella per advisor


def _tables(path) -> set[str]:
    from sqlalchemy import create_engine, inspect

    return set(inspect(create_engine(f"sqlite:///{path}")).get_table_names())


def test_reading_market_prices_creates_neither_file_nor_tenant_tables(tmp_path, monkeypatch):
    from portfolio_intelligence.data import store

    db = tmp_path / "investor.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db}")
    assert store.load_prices() is None
    assert store.last_date() is None
    assert store.known_tickers() == []
    assert not db.exists()  # una lettura non crea il database


def test_saving_market_prices_creates_only_the_prices_table(tmp_path, monkeypatch):
    from portfolio_intelligence.data import store

    db = tmp_path / "market.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db}")
    prices = pd.DataFrame({"AAPL": [100.0, 101.0]}, index=pd.bdate_range("2026-01-05", periods=2))
    store.save_prices(prices)
    assert _tables(db) == {"prices"}
    assert store.known_tickers() == ["AAPL"]
    # l'area Advisor aggiunge le sue tabelle solo quando le usa
    store.get_engine()
    assert {"portfolios", "analyses", "audit_log"} <= _tables(db)


def test_investor_market_loader_never_creates_tenant_tables(tmp_path, monkeypatch):
    from portfolio_intelligence.data import store
    from portfolio_intelligence.views import common

    db = tmp_path / "shared.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db}")
    store.save_prices(
        pd.DataFrame({"MSFT": [400.0]}, index=pd.bdate_range("2026-01-05", periods=1))
    )
    common._cached_market_db.clear()
    loaded = common.load_market_db()
    assert loaded is not None and list(loaded.columns) == ["MSFT"]
    assert _tables(db) == {"prices"}


def test_sqlite_urls_with_parameters_and_drivers(tmp_path):
    from portfolio_intelligence.data import store

    db = tmp_path / "params.db"
    assert store.sqlite_file(f"sqlite:///{db}?timeout=30") == db
    assert store.sqlite_file(f"sqlite+pysqlite:///{db}") == db
    assert store.sqlite_file("sqlite:///:memory:") is None
    assert store.sqlite_file("postgresql+psycopg://u:p@host/db") is None
    engine = store.market_engine(f"sqlite:///{db}?timeout=30")
    store.save_prices(
        pd.DataFrame({"AAPL": [1.0]}, index=pd.bdate_range("2026-01-05", periods=1)), engine
    )
    assert store.known_tickers(engine) == ["AAPL"]  # i parametri non nascondono i dati


def _first_writes_race(url: str) -> list:
    """Due prime scritture dei prezzi e un primo accesso Advisor, nello stesso istante."""
    import threading

    from portfolio_intelligence.data import store

    barrier = threading.Barrier(3)
    errors: list = []
    frame = pd.DataFrame({"AAPL": [1.0]}, index=pd.bdate_range("2026-01-05", periods=1))
    engine = store.market_engine(url)

    def run(job):
        barrier.wait()
        try:
            job()
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    jobs = [
        lambda: store.save_prices(frame, engine),
        lambda: store.save_prices(frame, engine),
        lambda: store.get_engine(url),
    ]
    threads = [threading.Thread(target=run, args=(job,)) for job in jobs]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(10)
    return errors


def test_concurrent_first_writes_do_not_collide(tmp_path):
    for trial in range(15):
        assert _first_writes_race(f"sqlite:///{tmp_path / f'race{trial}.db'}") == []
