"""Smarteefinance Investor (B2C stateless) vs Advisor (B2B stateful): confini.

Copre ROADMAP.md — split dei router. Due livelli di verifica:
- funzionale: chiama sidebar.render_sidebar/checkup.render in bare mode
  (stesso pattern di test_tenant_isolation.py per admin.render) con le
  funzioni di store.py sostituite da una che solleva se chiamata — se
  Investor è davvero stateless, non devono mai scattare.
- strutturale: l'entry point giusto importa/chiama le cose giuste (nessuna
  chiamata di rete, solo lettura di sorgente — vedi ROADMAP "Principi non
  negoziabili").
"""

import numpy as np
import pandas as pd
import pytest

from portfolio_intelligence import router as router_mod
from portfolio_intelligence.analytics.pipeline import analyze_portfolio
from portfolio_intelligence.portfolio.positions import normalize_portfolio
from portfolio_intelligence.views import checkup as checkup_mod
from portfolio_intelligence.views import sidebar as sidebar_mod
from portfolio_intelligence.views.context import ViewContext
from portfolio_intelligence.views.sidebar import SidebarSettings

RNG = np.random.default_rng(21)
DAYS = 260
INDEX = pd.bdate_range("2025-01-02", periods=DAYS)


def _prices(cols: dict[str, float]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            name: 100 * (1 + pd.Series(RNG.normal(drift, 0.012, DAYS), index=INDEX)).cumprod()
            for name, drift in cols.items()
        }
    )


PRICES = _prices({"AAA": 0.0006, "BBB": 0.0003, "CCC": 0.0004})
BENCH = _prices({"QQQ": 0.0005})
PORTFOLIO = [
    {"ticker": "AAA", "weight": 0.5},
    {"ticker": "BBB", "weight": 0.3},
    {"ticker": "CCC", "weight": 0.2},
]
FUND = pd.DataFrame(
    float("nan"),
    index=["AAA", "BBB", "CCC"],
    columns=["revenue_growth", "net_margin", "debt_to_equity", "pe", "ps", "name"],
)


@pytest.fixture(scope="module")
def computed() -> dict:
    c = analyze_portfolio(PRICES, BENCH, PORTFOLIO, FUND, benchmark="QQQ")
    c["prices"] = PRICES  # checkup.render legge c["prices"] per le note di copertura
    return c


def _ctx(computed: dict, *, stateful: bool) -> ViewContext:
    return ViewContext(
        computed=computed,
        amounts={"AAA": 5000.0, "BBB": 3000.0, "CCC": 2000.0},
        total=10000.0,
        portfolio=PORTFOLIO,
        portfolio_name="Test",
        period="1y",
        in_eur=True,
        risk_free=0.02,
        risk_profile="Not set",
        advisor="local@dev",
        names={},
        pos=None,
        pnl_totals={"cost": 9000.0, "pnl": 1000.0, "pnl_pct": 0.11},
        irr=0.15,
        stateful=stateful,
    )


def _boom(*_a, **_k):
    raise AssertionError("store.py function called when it should not have been")


# --------------------------------------------------- router.compute_portfolio (pipeline)


def test_compute_portfolio_empty_positions_short_circuits():
    result = router_mod.compute_portfolio(
        {}, SidebarSettings("My portfolio", "1y", True, 0.02, "Not set")
    )
    assert result.computed is None
    assert result.total == 0.0
    assert result.portfolio == []


def test_compute_portfolio_builds_the_same_shape_as_the_old_app_py(monkeypatch):
    positions = normalize_portfolio(
        {
            "AAA": {"lots": [{"qty": 10.0, "price": 90.0, "date": "2025-01-10"}]},
            "BBB": {"lots": [{"qty": 5.0, "price": 180.0, "date": "2025-02-01"}]},
        }
    )
    fund = pd.DataFrame(
        float("nan"),
        index=["AAA", "BBB"],
        columns=["revenue_growth", "net_margin", "debt_to_equity", "pe", "ps"],
    )
    fund["name"] = {"AAA": "Alpha Inc", "BBB": "Beta Corp"}
    eurusd = pd.Series(1.08, index=INDEX)

    monkeypatch.setattr(router_mod, "cached_prices", lambda tickers, period: _prices_for(tickers))
    monkeypatch.setattr(router_mod, "cached_eurusd", lambda period: eurusd)
    monkeypatch.setattr(
        router_mod, "analysis_fundamentals", lambda tickers: fund.loc[list(tickers)]
    )

    import streamlit as st

    st.session_state["names"] = {}
    result = router_mod.compute_portfolio(
        positions, SidebarSettings("My portfolio", "1y", True, 0.02, "Not set")
    )

    assert result.computed is not None
    assert result.compute_error is None
    assert set(result.amounts) == {"AAA", "BBB"}
    assert result.total > 0
    assert result.irr is not None
    assert result.names == {"AAA": "Alpha Inc", "BBB": "Beta Corp"}


def _prices_for(tickers: tuple[str, ...]) -> pd.DataFrame:
    cols = {t: 0.0005 for t in tickers}
    return _prices(cols)


# -------------------------------------------------------- sidebar: Investor vs Advisor


def test_investor_sidebar_has_no_access_to_the_portfolio_store(monkeypatch):
    """La sidebar è solo Investor: non importa store.py, quindi non può
    leggere né scrivere portafogli, analisi o audit log."""
    import streamlit as st

    with open(sidebar_mod.__file__) as f:
        assert "data.store" not in f.read()
    monkeypatch.setattr(sidebar_mod, "cached_risk_free", lambda: 0.03)
    st.session_state.positions = {}

    settings = sidebar_mod.render_sidebar()

    assert settings.portfolio_name == "My portfolio"


# -------------------------------------------------------- check-up: Investor vs Advisor


def test_checkup_investor_mode_never_touches_analyses_store(monkeypatch, computed):
    monkeypatch.setattr(checkup_mod, "log_analysis", _boom)
    monkeypatch.setattr(checkup_mod, "log_audit", _boom)
    monkeypatch.setattr(checkup_mod, "load_analyses", _boom)

    checkup_mod.render(_ctx(computed, stateful=False))  # non deve sollevare


def test_checkup_advisor_mode_does_read_the_analyses_store(monkeypatch, computed):
    calls = {"load_analyses": False}
    monkeypatch.setattr(
        checkup_mod,
        "load_analyses",
        lambda *a, **k: calls.__setitem__("load_analyses", True) or pd.DataFrame(),
    )

    checkup_mod.render(_ctx(computed, stateful=True))

    assert calls["load_analyses"] is True


# ------------------------------------------------- entry point: struttura e confini


def test_app_investor_defaults_require_auth_off():
    with open("app_investor.py") as f:
        source = f.read()
    assert 'bootstrap_page("Smarteefinance Investor | Portfolio Check-up", False)' in source


def test_app_advisor_defaults_require_auth_on():
    with open("app_advisor.py") as f:
        source = f.read()
    assert (
        'bootstrap_page("Smarteefinance Advisor | Professional Portfolio Intelligence", True)'
        in source
    )


def test_app_investor_never_imports_clients_or_admin_views():
    with open("app_investor.py") as f:
        source = f.read()
    # controlla l'uso in codice, non la prosa nei commenti/docstring (che
    # spiegano legittimamente perché Admin/Clients sono esclusi)
    assert "import clients" not in source and "clients.render" not in source
    assert "import admin" not in source and "admin.render" not in source
    assert "is_admin(" not in source  # nessun concetto di ruolo per un utente anonimo


def test_app_investor_sidebar_and_context_are_non_persistent():
    with open("app_investor.py") as f:
        source = f.read()
    assert "render_sidebar()" in source
    assert "stateful=False" in source


def test_app_advisor_keeps_admin_gate_and_multi_tenant_identity():
    with open("app_advisor.py") as f:
        entry = f.read()
    with open("portfolio_intelligence/views/advisor_workspace.py") as f:
        workspace = f.read()
    assert "current_advisor()" in entry  # isolamento per tenant, non un advisor fisso
    assert "advisor_workspace.render(advisor)" in entry
    assert "is_admin(advisor)" in workspace  # Admin solo per gli admin
    assert "stateful=True" in workspace


def _resolve_app_profile(namespace: dict) -> None:
    """Esegue solo la logica di risoluzione del profilo in app.py (fino a
    "if run_app is not None:"), senza eseguire il dispatch/rendering reale —
    stesso principio dei test precedenti su questo file, adattato alla nuova
    struttura (router con schermata di scelta, non più dispatch diretto)."""
    with open("app.py") as f:
        source = f.read()
    setup_source = source.split("if run_app is not None:")[0]
    exec(compile(setup_source, "app.py", "exec"), namespace)


def test_app_router_no_profile_falls_through_to_chooser(monkeypatch):
    """Senza APP_MODE e senza ?profile= in query_params, il router non deve
    scegliere un profilo da solo — run_app resta None, che nel resto del
    file fa renderizzare render_profile_chooser() invece di saltare a un
    'advisor' silenzioso (comportamento storico, ora sostituito dalla
    schermata di scelta esplicita)."""
    monkeypatch.delenv("APP_MODE", raising=False)
    import streamlit as st

    st.query_params.clear()

    namespace: dict = {"os": __import__("os"), "st": st}
    _resolve_app_profile(namespace)

    assert not namespace["profile"]
    assert namespace["run_app"] is None


def test_app_router_app_mode_env_var_skips_chooser(monkeypatch):
    """APP_MODE impostato esplicitamente (deploy automatizzato) salta la
    schermata di scelta e va dritto al profilo — comportamento invariato
    per chi già lo usa così."""
    monkeypatch.setenv("APP_MODE", "advisor")
    import streamlit as st

    st.query_params.clear()

    namespace: dict = {"os": __import__("os"), "st": st}
    _resolve_app_profile(namespace)

    assert namespace["profile"] == "advisor"
    assert namespace["run_app"] is not None


def test_app_router_query_param_selects_profile_like_a_click_would(monkeypatch):
    """Cliccare una card della chooser imposta ?profile= in query_params
    (vedi _go_investor/_go_advisor) — qui si verifica che il router onori
    quel valore esattamente come onorerebbe APP_MODE."""
    monkeypatch.delenv("APP_MODE", raising=False)
    import streamlit as st

    st.query_params.clear()
    st.query_params["profile"] = "investor"

    namespace: dict = {"os": __import__("os"), "st": st}
    _resolve_app_profile(namespace)

    assert namespace["profile"] == "investor"
    assert namespace["run_app"] is not None

    st.query_params.clear()


def test_app_router_renders_chooser_without_forcing_require_auth(monkeypatch):
    """Il router non deve più toccare REQUIRE_AUTH per conto proprio: la
    rete di sicurezza del fix precedente serviva a non bloccare un dispatch
    silenzioso ad Advisor, dispatch che ora non esiste più (serve un click
    esplicito). Se la chooser venisse mai rimossa per errore senza
    rimuovere anche questa garanzia, questo test lo segnalerebbe."""
    with open("app.py") as f:
        source = f.read()
    assert "resolve_require_auth" not in source
    assert "render_profile_chooser" in source
