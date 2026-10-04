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
    gate_pos = source.index("auth_required_but_missing()", def_pos)
    # dopo il gate, bootstrap_page non fa più nient'altro che st.stop()
    next_def_pos = source.index("\ndef ", gate_pos)
    assert def_pos < gate_pos < next_def_pos


@pytest.mark.parametrize("entry_point", ["app_advisor.py", "app_investor.py"])
def test_entry_points_bootstrap_before_gate_before_sidebar(entry_point):
    """Regressione strutturale: ciascun entry point deve chiamare
    bootstrap_page() (che include il gate REQUIRE_AUTH) PRIMA del gate di
    onboarding, PRIMA della sidebar — l'ordine conta, non solo la presenza."""
    with open(entry_point) as f:
        source = f.read()
    bootstrap_pos = source.index("bootstrap_page(")
    onboarding_pos = source.index("gate.render_gate()")
    sidebar_pos = source.index("render_sidebar(")
    assert bootstrap_pos < onboarding_pos < sidebar_pos


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
