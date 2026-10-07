"""Universi di riferimento: il benchmark scelto guida beta, alfa e confronti (nessuna rete).

Copre la catena intera: registro (data/benchmarks.py) → simbologia dei provider
→ valuta → persistenza per cliente e storico degli indici → pipeline e report
che misurano contro il benchmark passato, non contro uno fisso.
"""

import zlib

import numpy as np
import pandas as pd
import pytest

from portfolio_intelligence.analytics.performance import beta_alpha, rolling_beta
from portfolio_intelligence.analytics.pipeline import analyze_portfolio
from portfolio_intelligence.analytics.report_metrics import compute_report_metrics
from portfolio_intelligence.data.benchmarks import (
    BENCHMARK_TICKERS,
    BENCHMARKS,
    DEFAULT_BENCHMARK,
    benchmark_label,
    benchmark_or_default,
    is_price_index,
)
from portfolio_intelligence.data.fx import convert_to_eur, is_usd_listing
from portfolio_intelligence.data.providers import (
    EODHDProvider,
    ProviderError,
    StooqProvider,
    eodhd_symbol,
    stooq_symbol,
)
from portfolio_intelligence.fundamentals.valuation import empty_fundamentals

N_DAYS = 400
INDEX = pd.bdate_range("2024-01-02", periods=N_DAYS + 1)


@pytest.fixture(autouse=True)
def _dispose_engines():
    """Chiude i motori SQLite aperti dal test sui DB temporanei (nessuna connessione orfana)."""
    from portfolio_intelligence.data import store

    before = set(store._ENGINES)
    yield
    for url in set(store._ENGINES) - before:
        store._ENGINES.pop(url).dispose()


def _factors(seed: int = 3) -> tuple[pd.Series, pd.Series]:
    """Due fattori di mercato con covarianza campionaria nulla: i beta attesi sono esatti."""
    rng = np.random.default_rng(seed)
    a = rng.normal(0.0004, 0.011, N_DAYS)
    b = rng.normal(0.0002, 0.009, N_DAYS)
    a_c = a - a.mean()
    b = b - np.dot(b - b.mean(), a_c) / np.dot(a_c, a_c) * a_c
    return pd.Series(a, index=INDEX[1:]), pd.Series(b, index=INDEX[1:])


def _prices_from(returns: pd.Series) -> pd.Series:
    """Prezzi base 100 i cui rendimenti giornalieri sono esattamente `returns`."""
    return pd.concat([pd.Series([100.0], index=INDEX[:1]), 100 * (1 + returns).cumprod()])


# ---------------------------------------------------------- beta al variare del benchmark


def test_beta_and_alpha_follow_the_benchmark_series_passed_in():
    a, b = _factors()
    portfolio = 1.5 * a + 0.4 * b

    beta_a, alpha_a = beta_alpha(portfolio, a)
    beta_b, alpha_b = beta_alpha(portfolio, b)

    assert beta_a == pytest.approx(1.5)
    assert beta_b == pytest.approx(0.4)
    # alfa: la parte di rendimento non spiegata da QUEL benchmark
    assert alpha_a == pytest.approx(0.4 * b.mean() * 252)
    assert alpha_b == pytest.approx(1.5 * a.mean() * 252)


def _computed_against(benchmark: str) -> dict:
    """Pipeline completa: portafoglio = 1,5 × S&P 500 + 0,4 × FTSE MIB (fattori sintetici)."""
    a, b = _factors()
    pf = _prices_from(1.5 * a + 0.4 * b)
    prices = pd.DataFrame({"AAA": pf, "BBB": pf})
    bench_prices = pd.DataFrame(
        {
            "^GSPC": _prices_from(a),
            "FTSEMIB.MI": _prices_from(b),
            "QQQ": _prices_from(0.7 * a + 0.7 * b),
        }
    )
    portfolio = [{"ticker": "AAA", "weight": 0.5}, {"ticker": "BBB", "weight": 0.5}]
    return analyze_portfolio(
        prices, bench_prices, portfolio, empty_fundamentals(["AAA", "BBB"]), benchmark
    )


@pytest.mark.parametrize(
    ("benchmark", "expected_beta"), [("^GSPC", 1.5), ("FTSEMIB.MI", 0.4), ("QQQ", None)]
)
def test_pipeline_measures_beta_against_the_chosen_benchmark(benchmark, expected_beta):
    computed = _computed_against(benchmark)
    a, b = _factors()

    assert computed["benchmark"] == benchmark
    assert computed["bench_daily"].name == benchmark
    expected = expected_beta
    if expected is None:  # QQQ = 0,7a + 0,7b: beta dalla definizione
        q = 0.7 * a + 0.7 * b
        expected = float((1.5 * a + 0.4 * b).cov(q) / q.var())
    assert computed["beta"] == pytest.approx(expected, rel=1e-6)


def test_switching_benchmark_changes_beta_but_not_the_portfolio_metrics():
    spx, mib = _computed_against("^GSPC"), _computed_against("FTSEMIB.MI")

    assert spx["beta"] != pytest.approx(mib["beta"], abs=0.5)
    assert spx["alpha"] != pytest.approx(mib["alpha"])
    for key in ("annual_ret", "annual_vol", "drawdown", "var_95", "health", "risk_score"):
        assert spx[key] == pytest.approx(mib[key]), key


def test_pipeline_rejects_a_benchmark_without_prices():
    a, _ = _factors()
    prices = pd.DataFrame({"AAA": _prices_from(a)})
    with pytest.raises(ValueError, match="FTSEMIB.MI"):
        analyze_portfolio(
            prices,
            pd.DataFrame({"QQQ": _prices_from(a)}),
            [{"ticker": "AAA", "weight": 1.0}],
            empty_fundamentals(["AAA"]),
            "FTSEMIB.MI",
        )


def test_default_benchmark_comes_from_the_registry():
    a, _ = _factors()
    prices = pd.DataFrame({"AAA": _prices_from(a)})
    bench = pd.DataFrame({DEFAULT_BENCHMARK: _prices_from(a)})
    computed = analyze_portfolio(
        prices, bench, [{"ticker": "AAA", "weight": 1.0}], empty_fundamentals(["AAA"])
    )
    assert computed["benchmark"] == DEFAULT_BENCHMARK
    assert computed["beta"] == pytest.approx(1.0)


def test_rolling_beta_follows_the_benchmark_passed_in():
    a, b = _factors()
    portfolio = 2.0 * a

    against_a = rolling_beta(portfolio, a, window=60)
    against_b = rolling_beta(portfolio, b, window=60)

    assert len(against_a) == N_DAYS - 60 + 1
    assert against_a.to_numpy() == pytest.approx(np.full(len(against_a), 2.0))
    assert not np.allclose(against_b.to_numpy(), 2.0)


def test_rolling_beta_aligns_dates_and_skips_flat_benchmark_windows():
    a, _ = _factors()
    bench = pd.concat([pd.Series(0.0, index=a.index[:80]), a.iloc[80:]])
    beta = rolling_beta(2.0 * a.iloc[10:], bench, window=20)

    # le finestre con benchmark piatto (varianza nulla) non producono un beta
    assert beta.index.min() == a.index[80]
    # dove il benchmark è il fattore stesso, beta = 2 sulle sole date comuni
    tail = beta.loc[a.index[99] :]
    assert tail.to_numpy() == pytest.approx(np.full(len(tail), 2.0))


def test_report_metrics_beta_follows_the_benchmark():
    for benchmark in ("^GSPC", "FTSEMIB.MI"):
        computed = _computed_against(benchmark)
        metrics = compute_report_metrics(
            computed["pf_daily"],
            computed["bench_daily"],
            pd.Series({"AAA": 0.5, "BBB": 0.5}),
            computed["contributions"],
            computed["fund"],
            computed["usd_weight"],
        )
        assert metrics.beta == pytest.approx(computed["beta"])


# ---------------------------------------------------------- registro


def test_registry_covers_the_required_universes():
    assert set(BENCHMARK_TICKERS) == {"QQQ", "^GSPC", "FTSEMIB.MI", "^STOXX"}
    assert DEFAULT_BENCHMARK in BENCHMARKS
    assert len({b.label for b in BENCHMARKS.values()}) == len(BENCHMARKS)
    assert {b.currency for b in BENCHMARKS.values()} <= {"USD", "EUR"}


def test_registry_helpers():
    assert benchmark_or_default(None) == DEFAULT_BENCHMARK  # record storici
    assert benchmark_or_default("^XYZ") == DEFAULT_BENCHMARK
    assert benchmark_or_default("^STOXX") == "^STOXX"
    assert benchmark_label("^GSPC") == "S&P 500"
    assert benchmark_label("^XYZ") == "^XYZ"  # mai un'etichetta sbagliata
    assert is_price_index("FTSEMIB.MI")
    assert not is_price_index("QQQ")  # ETF: dividendi nel prezzo rettificato
    assert not is_price_index("^XYZ")


# ---------------------------------------------------------- simbologia dei provider


def test_provider_symbols_for_indices_and_stocks():
    assert stooq_symbol("^GSPC") == "^spx"
    assert stooq_symbol("QQQ") == "qqq.us"
    assert stooq_symbol("AAPL") == "aapl.us"
    assert stooq_symbol("^STOXX") is None  # non coperto: mai un simbolo inventato
    assert stooq_symbol("^VIX") is None
    assert eodhd_symbol("^GSPC") == "GSPC.INDX"
    assert eodhd_symbol("FTSEMIB.MI") == "FTSEMIB.INDX"
    assert eodhd_symbol("^STOXX") == "SXXP.INDX"
    assert eodhd_symbol("AAPL") == "AAPL.US"
    assert eodhd_symbol("^VIX") is None


class _CsvResp:
    status_code = 200
    text = "Date,Open,High,Low,Close\n2026-01-02,1,1,1,5000.0\n2026-01-05,1,1,1,5050.0\n"

    def raise_for_status(self):
        pass


def test_stooq_queries_mapped_symbols_and_skips_uncovered_indices(monkeypatch):
    requested: list[str] = []

    def fake_get(url, params, headers, timeout):
        requested.append(params["s"])
        return _CsvResp()

    monkeypatch.setattr("portfolio_intelligence.data.providers.requests.get", fake_get)
    data = StooqProvider().fetch(["^GSPC", "^STOXX"], "1y")

    assert requested == ["^spx"]
    assert list(data.columns) == ["^GSPC"]  # colonne sempre in simbologia Yahoo
    assert data["^GSPC"].tolist() == [5000.0, 5050.0]

    requested.clear()
    with pytest.raises(ProviderError):
        StooqProvider().fetch(["^STOXX"], "1y")
    assert requested == []


def test_eodhd_queries_the_index_exchange(monkeypatch):
    urls: list[str] = []

    class FakeResp:
        def raise_for_status(self):
            pass

        def json(self):
            return [{"date": "2026-01-02", "close": 40000.0, "adjusted_close": 40000.0}]

    def fake_get(url, **_kwargs):
        urls.append(url)
        return FakeResp()

    monkeypatch.setattr("portfolio_intelligence.data.providers.requests.get", fake_get)
    data = EODHDProvider("key").fetch(["FTSEMIB.MI", "AAPL"], "1y")

    assert urls == [
        "https://eodhd.com/api/eod/FTSEMIB.INDX",
        "https://eodhd.com/api/eod/AAPL.US",
    ]
    assert set(data.columns) == {"FTSEMIB.MI", "AAPL"}


# ---------------------------------------------------------- valuta


def test_benchmark_currency_comes_from_the_registry():
    assert is_usd_listing("^GSPC") is True
    assert is_usd_listing("QQQ") is True
    assert is_usd_listing("FTSEMIB.MI") is False
    assert is_usd_listing("^STOXX") is False  # nessun suffisso, ma quota in EUR


def test_eur_benchmarks_are_not_converted():
    index = pd.bdate_range("2026-01-02", periods=3)
    prices = pd.DataFrame(
        {"^GSPC": [110.0, 121.0, 132.0], "^STOXX": [500.0, 505.0, 510.0]}, index=index
    )
    converted = convert_to_eur(prices, pd.Series([1.10, 1.10, 1.20], index=index))

    assert converted["^GSPC"].tolist() == pytest.approx([100.0, 110.0, 110.0])
    assert converted["^STOXX"].tolist() == pytest.approx([500.0, 505.0, 510.0])


# ---------------------------------------------------------- persistenza


def _engine(tmp_path):
    from portfolio_intelligence.data.store import get_engine

    return get_engine(f"sqlite:///{tmp_path / 'bench.db'}")


def test_client_benchmark_is_saved_kept_and_isolated(tmp_path):
    from portfolio_intelligence.data.store import create_client, list_clients, save_portfolio

    engine = _engine(tmp_path)
    create_client(
        "adv@a", "C-IT", {"ENEL.MI": 1.0}, "Moderate", engine=engine, benchmark="FTSEMIB.MI"
    )
    save_portfolio("adv@a", "C-US", {"AAPL": 1.0}, engine=engine, benchmark="^GSPC")
    save_portfolio("adv@a", "C-NEW", {"AAPL": 1.0}, engine=engine)
    # salvare solo le posizioni non tocca il benchmark già scelto
    save_portfolio("adv@a", "C-IT", {"ENI.MI": 2.0}, engine=engine)

    clients = list_clients("adv@a", engine=engine)
    assert clients["C-IT"]["benchmark"] == "FTSEMIB.MI"
    assert clients["C-IT"]["positions"] == {"ENI.MI": 2.0}
    assert clients["C-US"]["benchmark"] == "^GSPC"
    assert clients["C-NEW"]["benchmark"] == DEFAULT_BENCHMARK
    assert list_clients("adv@b", engine=engine) == {}

    save_portfolio("adv@a", "C-IT", {"ENI.MI": 2.0}, engine=engine, benchmark="^STOXX")
    assert list_clients("adv@a", engine=engine)["C-IT"]["benchmark"] == "^STOXX"


def test_unknown_benchmark_is_rejected_on_write_and_defaulted_on_read(tmp_path):
    from sqlalchemy import text

    from portfolio_intelligence.data.store import create_client, list_clients, save_portfolio

    engine = _engine(tmp_path)
    with pytest.raises(ValueError, match="benchmark"):
        save_portfolio("adv@a", "C-1", {"AAPL": 1.0}, engine=engine, benchmark="^N225")
    with pytest.raises(ValueError, match="benchmark"):
        create_client("adv@a", "C-1", {"AAPL": 1.0}, engine=engine, benchmark="SPY")
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO portfolios (advisor, name, positions, updated, benchmark) "
                "VALUES ('adv@a', 'ODD', '{\"AAPL\": 1.0}', '2025-01-01', '^N225')"
            )
        )
    assert list_clients("adv@a", engine=engine)["ODD"]["benchmark"] == DEFAULT_BENCHMARK


def test_pre_existing_database_gets_the_benchmark_column(tmp_path):
    """DB creato prima di questa versione: la colonna arriva da sola, i clienti restano."""
    from sqlalchemy import create_engine, inspect, text

    from portfolio_intelligence.data.store import get_engine, list_clients

    url = f"sqlite:///{tmp_path / 'old.db'}"
    old = create_engine(url)
    with old.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE portfolios (advisor VARCHAR, name VARCHAR, positions TEXT, "
                "updated VARCHAR, risk_profile VARCHAR, PRIMARY KEY (advisor, name))"
            )
        )
        conn.execute(
            text(
                "INSERT INTO portfolios VALUES "
                "('adv@a', 'C-OLD', '{\"AAPL\": 1.0}', '2025-01-01', 'Moderate')"
            )
        )
    old.dispose()

    engine = get_engine(url)

    assert "benchmark" in {c["name"] for c in inspect(engine).get_columns("portfolios")}
    client = list_clients("adv@a", engine=engine)["C-OLD"]
    assert client["benchmark"] == DEFAULT_BENCHMARK
    assert client["risk_profile"] == "Moderate"


def test_benchmark_history_is_replaced_and_kept_apart_from_stock_prices(tmp_path):
    from portfolio_intelligence.data.store import (
        known_tickers,
        load_benchmark_prices,
        load_prices,
        save_benchmark_prices,
    )

    engine = _engine(tmp_path)
    days = pd.bdate_range("2026-01-02", periods=4)
    first = pd.DataFrame(
        {"^GSPC": [1.0, 2.0, 3.0, 4.0], "^STOXX": [5.0, 6.0, 7.0, 8.0]}, index=days
    )
    assert save_benchmark_prices(first, engine=engine) == 8

    # nuovo download di un solo indice: riscrive quello, non tocca l'altro
    save_benchmark_prices(pd.DataFrame({"^GSPC": [9.0, 10.0]}, index=days[2:]), engine=engine)

    spx = load_benchmark_prices("^GSPC", engine=engine)
    assert spx is not None
    assert spx.tolist() == [9.0, 10.0]
    assert load_benchmark_prices("^STOXX", engine=engine).tolist() == [5.0, 6.0, 7.0, 8.0]
    window = load_benchmark_prices("^STOXX", start="2026-01-06", engine=engine)
    assert window.index[0] == pd.Timestamp("2026-01-06")
    assert load_benchmark_prices("FTSEMIB.MI", engine=engine) is None
    # gli indici non entrano nell'universo dei titoli (Mercato, ricerca, backtest)
    assert known_tickers(engine=engine) == []
    assert load_prices(engine=engine) is None


def test_constituents_are_replaced_per_benchmark(tmp_path):
    from portfolio_intelligence.data.store import load_constituents, save_constituents

    engine = _engine(tmp_path)
    old = pd.DataFrame({"name": ["Old Co"], "weight": [1.0]}, index=pd.Index(["OLD"]))
    save_constituents("QQQ", old, as_of="2026-01-01", engine=engine)
    new = pd.DataFrame(
        {"name": ["Apple", "Nvidia", "Apple dup"], "weight": [0.08, float("nan"), 0.5]},
        index=pd.Index(["AAPL", "NVDA", "AAPL"]),
    )
    assert save_constituents("QQQ", new, as_of="2026-10-07", engine=engine) == 2
    save_constituents("^GSPC", pd.DataFrame(index=pd.Index(["MSFT"])), engine=engine)

    saved = load_constituents("QQQ", engine=engine)
    assert list(saved.index) == ["AAPL", "NVDA"]
    assert saved.loc["AAPL", "weight"] == pytest.approx(0.08)  # il primo, non il duplicato
    assert pd.isna(saved.loc["NVDA", "weight"])
    assert set(saved["as_of"]) == {"2026-10-07"}
    assert list(load_constituents("^GSPC", engine=engine).index) == ["MSFT"]
    assert load_constituents("FTSEMIB.MI", engine=engine).empty
    with pytest.raises(ValueError, match="benchmark"):
        save_constituents("^N225", old, engine=engine)


# ---------------------------------------------------------- ingestion


def _series_for(ticker: str, days: int = 30) -> pd.DataFrame:
    rng = np.random.default_rng(zlib.crc32(ticker.encode()))
    index = pd.bdate_range("2026-01-02", periods=days)
    return pd.DataFrame(
        {ticker: 100 * np.cumprod(1 + rng.normal(0.0003, 0.01, days))}, index=index
    )


def test_ingestion_downloads_each_benchmark_with_its_own_fallback(tmp_path, monkeypatch, capsys):
    import download_nasdaq100 as dl
    from portfolio_intelligence.data.store import load_benchmark_prices

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'market.db'}")
    calls: list[tuple[list[str], str]] = []

    class FakeChain:
        def fetch(self, tickers, period):
            calls.append((list(tickers), period))
            if tickers == ["^STOXX"]:
                raise ValueError("No data provider responded")
            return _series_for(tickers[0]), "Stub"

    monkeypatch.setattr(dl, "build_default_chain", lambda: FakeChain())
    saved = dl.update_benchmarks()

    assert [tickers for tickers, _ in calls] == [[t] for t in BENCHMARK_TICKERS]
    assert {period for _, period in calls} == {dl.FULL_PERIOD}
    assert set(saved) == set(BENCHMARK_TICKERS) - {"^STOXX"}  # uno manca, gli altri no
    assert len(load_benchmark_prices("FTSEMIB.MI")) == 30
    assert load_benchmark_prices("^STOXX") is None
    assert "STOXX 600 (^STOXX) non disponibile" in capsys.readouterr().out


def test_ingestion_saves_the_nasdaq100_composition(tmp_path, monkeypatch):
    import download_nasdaq100 as dl
    from portfolio_intelligence.data.store import load_constituents

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'market.db'}")
    constituents = pd.DataFrame(
        {"name": ["Apple Inc.", "NVIDIA Corp."], "weight": [0.09, 0.08]},
        index=pd.Index(["AAPL", "NVDA"], name="ticker"),
    )
    monkeypatch.setattr(dl, "get_nasdaq100_constituents", lambda: constituents)
    monkeypatch.setattr(dl, "load_nasdaq100_prices", lambda: None)
    monkeypatch.setattr(
        dl, "_download", lambda tickers, **_k: pd.concat([_series_for(t) for t in tickers], axis=1)
    )

    dl.update_nasdaq100()

    saved = load_constituents(dl.NASDAQ100_BENCHMARK)
    assert saved["name"].to_dict() == {"AAPL": "Apple Inc.", "NVDA": "NVIDIA Corp."}
    assert saved["weight"].tolist() == pytest.approx([0.09, 0.08])


def test_nasdaq100_constituents_carry_names_and_weights(monkeypatch):
    from portfolio_intelligence.data.yahoo_client import get_nasdaq100_constituents

    html = """<table>
    <tr><th>#</th><th>Company</th><th>Symbol</th><th>Weight</th></tr>
    <tr><td>1</td><td>Example Corp</td><td>EXMP</td><td>10.5%</td></tr>
    <tr><td>2</td><td>Sample Inc</td><td>SMPL</td><td>5.0%</td></tr>
    </table>"""

    class FakeResponse:
        text = html

        def raise_for_status(self):
            pass

    monkeypatch.setattr(
        "portfolio_intelligence.data.yahoo_client.requests.get", lambda *a, **k: FakeResponse()
    )
    frame = get_nasdaq100_constituents()

    assert list(frame.index) == ["EXMP", "SMPL"]
    assert frame["name"].tolist() == ["Example Corp", "Sample Inc"]
    assert frame["weight"].tolist() == pytest.approx([0.105, 0.05])
