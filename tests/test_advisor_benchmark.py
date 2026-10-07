"""Benchmark di riferimento per cliente nell'area Advisor: dal selettore al PDF (senza rete).

Il benchmark si sceglie alla creazione del cliente o nella scheda Posizioni, si
salva insieme a posizioni e profilo e arriva alla pipeline, alle viste di
analisi e al report: Panoramica e PDF di un cliente con titoli italiani si
confrontano con il FTSE MIB, non con il Nasdaq-100.
"""

import zlib
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from portfolio_intelligence import router as router_mod
from portfolio_intelligence.analytics.pipeline import analyze_portfolio
from portfolio_intelligence.data.benchmarks import DEFAULT_BENCHMARK
from portfolio_intelligence.data.store import list_clients, save_portfolio
from portfolio_intelligence.fundamentals.valuation import empty_fundamentals
from portfolio_intelligence.i18n import set_language, t_in
from portfolio_intelligence.portfolio.positions import normalize_portfolio
from portfolio_intelligence.views import advisor_overview as ov
from portfolio_intelligence.views import advisor_workspace as ws
from portfolio_intelligence.views import checkup, sidebar
from portfolio_intelligence.views.context import ViewContext
from portfolio_intelligence.views.sidebar import SidebarSettings

ADVISOR = "adv@x"
_REAL_CLIENT_ANALYSIS = ws._client_analysis  # prima che la fixture la sostituisca
INDEX = pd.bdate_range("2025-01-02", periods=260)


@pytest.fixture(autouse=True)
def _english():
    set_language("en")
    yield
    set_language("en")


@pytest.fixture(autouse=True)
def _dispose_engines():
    """Chiude i motori SQLite aperti dal test sui DB temporanei (nessuna connessione orfana)."""
    from portfolio_intelligence.data import store

    before = set(store._ENGINES)
    yield
    for url in set(store._ENGINES) - before:
        store._ENGINES.pop(url).dispose()


def _prices_for(tickers) -> pd.DataFrame:
    """Prezzi sintetici deterministici per ticker (stesso ticker, stessa serie)."""
    return pd.DataFrame(
        {
            ticker: 100
            * np.cumprod(
                1 + np.random.default_rng(zlib.crc32(ticker.encode())).normal(0.0004, 0.012, 260)
            )
            for ticker in tickers
        },
        index=INDEX,
    )


# ---------------------------------------------------------- router: dalle impostazioni alla pipeline

POSITIONS = normalize_portfolio(
    {
        "AAA": {"lots": [{"qty": 10.0, "price": 90.0, "date": "2025-01-10"}]},
        "BBB": {"lots": [{"qty": 5.0, "price": 180.0, "date": "2025-02-01"}]},
    }
)
EURUSD = pd.Series(np.linspace(1.0, 1.2, len(INDEX)), index=INDEX)  # cambio che si muove


@pytest.fixture
def market(monkeypatch):
    """Prezzi, cambio e fondamentali finti per router.compute_portfolio; registra le richieste."""
    import streamlit as st

    requested: list[tuple[str, ...]] = []

    def fake_prices(tickers, period):
        requested.append(tuple(tickers))
        return _prices_for(tickers)

    monkeypatch.setattr(router_mod, "cached_prices", fake_prices)
    monkeypatch.setattr(router_mod, "cached_eurusd", lambda period: EURUSD)
    monkeypatch.setattr(
        router_mod, "analysis_fundamentals", lambda tickers: empty_fundamentals(list(tickers))
    )
    st.session_state["names"] = {}
    return requested


def _settings(benchmark: str, in_eur: bool = True) -> SidebarSettings:
    return SidebarSettings("C-1", "1y", in_eur, 0.02, "Moderate", benchmark)


def test_compute_portfolio_uses_the_benchmark_in_the_settings(market):
    result = router_mod.compute_portfolio(POSITIONS, _settings("^GSPC"))

    assert result.compute_error is None
    assert ("^GSPC",) in market
    assert (DEFAULT_BENCHMARK,) not in market  # nessun benchmark fisso dietro le quinte
    assert result.computed["benchmark"] == "^GSPC"


def test_eur_benchmark_is_left_in_euro_while_usd_benchmark_is_converted(market):
    raw = {t: _prices_for([t])[t].pct_change().dropna() for t in ("FTSEMIB.MI", "^GSPC")}

    mib = router_mod.compute_portfolio(POSITIONS, _settings("FTSEMIB.MI")).computed
    spx = router_mod.compute_portfolio(POSITIONS, _settings("^GSPC")).computed

    assert mib["bench_daily"].to_numpy() == pytest.approx(raw["FTSEMIB.MI"].to_numpy())
    assert not np.allclose(spx["bench_daily"].to_numpy(), raw["^GSPC"].to_numpy())


def test_beta_differs_between_benchmarks_for_the_same_client(market):
    spx = router_mod.compute_portfolio(POSITIONS, _settings("^GSPC")).computed
    stoxx = router_mod.compute_portfolio(POSITIONS, _settings("^STOXX")).computed

    assert spx["beta"] != pytest.approx(stoxx["beta"])
    assert spx["annual_vol"] == pytest.approx(stoxx["annual_vol"])  # il portafoglio è lo stesso


def test_stored_history_backs_up_the_benchmark_when_providers_fail(market, monkeypatch):
    def prices_without_benchmark(tickers, period):
        if tickers == ("FTSEMIB.MI",):
            raise ValueError("No data provider responded")
        return _prices_for(tickers)

    stored = _prices_for(["FTSEMIB.MI"]).iloc[:-5]  # ingestion di qualche giorno fa
    monkeypatch.setattr(router_mod, "cached_prices", prices_without_benchmark)
    monkeypatch.setattr(router_mod, "stored_benchmark", lambda ticker, period: stored)

    result = router_mod.compute_portfolio(POSITIONS, _settings("FTSEMIB.MI"))

    assert result.compute_error is None
    assert result.computed["benchmark"] == "FTSEMIB.MI"
    assert "FTSE MIB" in result.notice
    assert f"{stored.index[-1]:%d/%m/%Y}" in result.notice  # dichiara fin dove arriva


def test_without_live_or_stored_history_the_analysis_reports_the_error(market, monkeypatch):
    def prices_without_benchmark(tickers, period):
        if tickers == ("^STOXX",):
            raise ValueError("No data provider responded")
        return _prices_for(tickers)

    monkeypatch.setattr(router_mod, "cached_prices", prices_without_benchmark)
    monkeypatch.setattr(router_mod, "stored_benchmark", lambda ticker, period: None)

    result = router_mod.compute_portfolio(POSITIONS, _settings("^STOXX"))

    assert result.computed is None
    assert "No data provider responded" in result.compute_error


# ---------------------------------------------------------- viste e report


def _ctx(benchmark: str) -> ViewContext:
    tickers = ["AAA", "BBB"]
    prices = _prices_for(tickers)
    portfolio = [{"ticker": "AAA", "weight": 0.6}, {"ticker": "BBB", "weight": 0.4}]
    computed = analyze_portfolio(
        prices, _prices_for([benchmark]), portfolio, empty_fundamentals(tickers), benchmark
    )
    return ViewContext(
        computed=computed,
        amounts={"AAA": 6000.0, "BBB": 4000.0},
        total=10_000.0,
        portfolio=portfolio,
        portfolio_name="C-IT",
        period="1y",
        in_eur=True,
        risk_free=0.03,
        risk_profile="Moderate",
        advisor=ADVISOR,
        pnl_totals={"cost": 9000.0, "pnl": 1000.0, "pnl_pct": 0.11},
        stateful=False,
        benchmark=benchmark,
    )


def test_view_context_describes_the_client_benchmark():
    assert _ctx("^GSPC").benchmark_label == "S&P 500"
    assert _ctx("^GSPC").benchmark_price_index
    assert not _ctx("QQQ").benchmark_price_index
    default = ViewContext(None, {}, 0.0, [], "", "1y", True, 0.0, "Not set", ADVISOR)
    assert default.benchmark == DEFAULT_BENCHMARK  # Investor e viste senza cliente


def test_overview_key_figures_compare_with_the_client_benchmark():
    cells = {label: (value, sub) for label, value, sub, _ in ov.key_figures(_ctx("FTSEMIB.MI"))}

    assert cells["Return 1y"][1].startswith("FTSE MIB: ")
    assert "FTSE MIB" in cells["Sharpe ratio"][1]
    assert not any("QQQ" in sub for _, sub in cells.values())


def test_report_input_carries_the_client_benchmark():
    report = checkup.report_input(_ctx("^STOXX"), "Summary.", [], [])

    assert report.benchmark == "STOXX 600"
    assert report.benchmark_price_index
    assert checkup.report_input(_ctx("QQQ"), "Summary.", [], []).benchmark_price_index is False


def _pdf_text(data: bytes) -> str:
    from io import BytesIO

    import pdfplumber

    with pdfplumber.open(BytesIO(data)) as pdf:
        return " ".join((page.extract_text() or "") for page in pdf.pages).replace("\n", " ")


def test_pdf_declares_a_price_index_benchmark(make_report):
    from portfolio_intelligence.visualization.pdf_advisor import build_advisor_report
    from portfolio_intelligence.visualization.pdf_report import build_investor_report

    priced = make_report(benchmark="FTSE MIB", benchmark_price_index=True)
    for build in (build_investor_report, build_advisor_report):
        text = _pdf_text(build(priced))
        assert "FTSE MIB is a price index" in text
        assert "QQQ" not in text  # nessun residuo del vecchio benchmark fisso

    assert "price index" not in _pdf_text(build_investor_report(make_report()))


def test_pdf_note_is_translated(make_report):
    from portfolio_intelligence.visualization.pdf_report import build_investor_report

    report = make_report(benchmark="S&P 500", benchmark_price_index=True, lang="it")
    assert "S&P 500 è un indice di prezzo" in _pdf_text(build_investor_report(report))


# ---------------------------------------------------------- spazio di lavoro (AppTest)


def _workspace_app():
    from portfolio_intelligence.views import advisor_workspace

    advisor_workspace.render("adv@x")


def _lots(ticker, qty=10.0):
    return {ticker: {"lots": [{"qty": qty, "price": 100.0, "date": "2025-01-02"}]}}


def _fake_analysis(items, _period, _in_eur, _lang="en"):
    return {
        "health": 70,
        "value": 1000.0,
        "invested": 900.0,
        "cum": 0.1,
        "pnl_pct": 0.11,
        "vol": 0.12,
        "problem": "finding",
        "top_ticker": next(iter(dict(items)), "n/a"),
        "top_weight": 1.0,
        "drawdown": -0.1,
        "asof": "2026-10-02",
    }


@pytest.fixture
def offline(tmp_path, monkeypatch):
    """DB temporaneo, nessuna rete: analisi e tasso privo di rischio finti."""
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'ws.db'}")
    monkeypatch.setattr(sidebar, "cached_risk_free", lambda: 0.03)
    monkeypatch.setattr(ws, "_client_analysis", lambda *a, **k: None)
    monkeypatch.setattr(ws, "quick_client_analysis", _fake_analysis)


def _button(at, label):
    return next(b for b in at.button if b.label == label)


def _section(at, section):
    at.session_state["adv_section"] = section
    return at.run()


def _unsaved(at) -> bool:
    return any(w.value == t_in("en", "adv.unsaved") for w in at.warning)


def test_new_client_is_saved_with_the_chosen_benchmark(offline):
    at = AppTest.from_function(_workspace_app).run()
    at.button(key="advnav_new").click().run()
    assert at.selectbox(key="adv_new_benchmark").value == DEFAULT_BENCHMARK
    at.text_input(key="adv_new_name").input("C-IT")
    at.selectbox(key="adv_new_benchmark").select("FTSEMIB.MI")
    at.session_state["positions"] = _lots("ENEL.MI")
    at.run()
    _button(at, t_in("en", "adv.create")).click().run()

    assert list_clients(ADVISOR)["C-IT"]["benchmark"] == "FTSEMIB.MI"
    assert at.session_state["adv_benchmark"] == "FTSEMIB.MI"
    assert not _unsaved(at)

    at.button(key="advnav_new").click().run()
    assert at.selectbox(key="adv_new_benchmark").value == DEFAULT_BENCHMARK  # nessun trascinamento


def test_benchmark_change_is_pending_until_saved_then_reaches_the_database(offline):
    save_portfolio(ADVISOR, "C-A", _lots("AAPL"), risk_profile="Moderate")

    at = AppTest.from_function(_workspace_app).run()
    at.button(key="adv_open_0").click().run()
    assert at.session_state["adv_benchmark"] == DEFAULT_BENCHMARK  # record senza scelta
    _section(at, "positions")
    at.selectbox(key="adv_bench_sel_C-A").select("^GSPC").run()

    assert _unsaved(at)
    assert list_clients(ADVISOR)["C-A"]["benchmark"] == DEFAULT_BENCHMARK

    _button(at, t_in("en", "adv.save")).click().run()
    client = list_clients(ADVISOR)["C-A"]
    assert client["benchmark"] == "^GSPC"
    assert client["risk_profile"] == "Moderate"  # salvato insieme, senza perdere il profilo
    assert not _unsaved(at)


def test_discard_restores_the_saved_benchmark_and_its_selector(offline):
    save_portfolio(ADVISOR, "C-A", _lots("AAPL"), benchmark="FTSEMIB.MI")

    at = AppTest.from_function(_workspace_app).run()
    at.button(key="adv_open_0").click().run()
    _section(at, "positions")
    at.selectbox(key="adv_bench_sel_C-A").select("^STOXX").run()
    assert _unsaved(at)

    at.button(key="adv_discard").click().run()

    assert at.session_state["adv_benchmark"] == "FTSEMIB.MI"
    assert at.selectbox(key="adv_bench_sel_C-A").value == "FTSEMIB.MI"
    assert not _unsaved(at)


def test_benchmark_belongs_to_one_client_only(offline):
    save_portfolio(ADVISOR, "C-A", _lots("AAPL"), benchmark="^GSPC")
    save_portfolio(ADVISOR, "C-B", _lots("ENEL.MI"), benchmark="FTSEMIB.MI")

    at = AppTest.from_function(_workspace_app).run()
    at.button(key="adv_open_0").click().run()
    assert at.session_state["adv_client"] == "C-A"
    _section(at, "positions")
    at.selectbox(key="adv_bench_sel_C-A").select("^STOXX").run()

    at.button(key="advnav_clients").click().run()
    at.button(key="adv_open_1").click().run()
    assert at.session_state["adv_client"] == "C-B"
    assert at.session_state["adv_benchmark"] == "FTSEMIB.MI"  # nessun trascinamento da C-A
    _section(at, "positions")
    assert at.selectbox(key="adv_bench_sel_C-B").value == "FTSEMIB.MI"

    at.button(key="advnav_clients").click().run()
    at.button(key="adv_open_0").click().run()
    assert at.session_state["adv_benchmark"] == "^STOXX"  # la bozza di C-A è rimasta sua
    assert list_clients(ADVISOR)["C-A"]["benchmark"] == "^GSPC"


def test_client_analysis_runs_against_the_saved_benchmark(offline, monkeypatch):
    seen: list[str] = []

    def fake_context(advisor, name, profile, benchmark, period, in_eur, risk_free):
        seen.append(benchmark)
        return SimpleNamespace(report_recipient=""), None, None

    monkeypatch.setattr(ws, "_client_analysis", _REAL_CLIENT_ANALYSIS)
    monkeypatch.setattr(ws, "_context", fake_context)
    monkeypatch.setattr(ws.advisor_overview, "render", lambda _ctx, recipient_field: None)
    monkeypatch.setattr(ws.metrics, "render", lambda _ctx: None)
    monkeypatch.setattr(ws.visual, "render", lambda _ctx: None)
    save_portfolio(ADVISOR, "C-IT", _lots("ENEL.MI"), benchmark="FTSEMIB.MI")

    at = AppTest.from_function(_workspace_app).run()
    at.button(key="adv_open_0").click().run()
    assert seen[-1] == "FTSEMIB.MI"  # Panoramica
    _section(at, "analysis")
    assert seen[-1] == "FTSEMIB.MI"  # Analisi
    assert not at.exception


def test_context_hands_the_client_benchmark_to_the_pipeline(monkeypatch):
    import streamlit as st

    seen = {}

    def fake_compute(positions, settings):
        seen["benchmark"] = settings.benchmark
        return router_mod.ComputedPortfolio(None, None, {}, 0.0, [], None, None, None, {})

    monkeypatch.setattr(ws, "compute_portfolio", fake_compute)
    st.session_state.positions = _lots("ENEL.MI")

    ctx, error, _notice = ws._context(ADVISOR, "C-IT", "Moderate", "FTSEMIB.MI", "5y", True, 0.03)

    assert error is None
    assert seen["benchmark"] == "FTSEMIB.MI"
    assert ctx.benchmark == "FTSEMIB.MI"
    assert ctx.benchmark_label == "FTSE MIB"


def test_book_export_includes_the_benchmark():
    row = {
        "name": "C-IT",
        "profile": "Moderate",
        "benchmark": "FTSEMIB.MI",
        **_fake_analysis((("ENEL.MI", None),), "5y", True),
    }
    frame = pd.read_csv(pd.io.common.BytesIO(ws._book_csv([row])))

    assert list(frame.columns[:3]) == ["name", "profile", "benchmark"]
    assert frame.loc[0, "benchmark"] == "FTSEMIB.MI"


def test_benchmark_options_put_the_default_first_and_flag_price_indices():
    assert ws.BENCHMARK_OPTIONS[0] == DEFAULT_BENCHMARK
    assert ws._benchmark_option("QQQ") == "Nasdaq-100 (ETF QQQ)"
    assert ws._benchmark_option("FTSEMIB.MI") == "FTSE MIB · price index"


def test_analysis_views_render_against_a_price_index_benchmark():
    """Panoramica, Analisi e Grafici con il S&P 500: etichette giuste e nota sui dividendi."""

    def app():
        from test_advisor_benchmark import _ctx

        from portfolio_intelligence.views import advisor_overview, metrics, visual

        ctx = _ctx("^GSPC")
        advisor_overview.render(ctx, lambda: "")
        metrics.render(ctx)
        visual.render(ctx)

    at = AppTest.from_function(app).run(timeout=60)

    assert not at.exception
    page = " ".join(str(el.value) for el in [*at.markdown, *at.caption, *at.metric])
    note = t_in("en", "bench.price_index_note", benchmark="S&P 500")
    assert sum(c.value == note for c in at.caption) == 2  # Panoramica e Analisi
    assert "Beta vs S&P 500" in " ".join(m.label for m in at.metric)
    assert "QQQ" not in page
