import pandas as pd
import pytest

from portfolio_intelligence.fundamentals import valuation
from portfolio_intelligence.fundamentals.valuation import empty_fundamentals, fetch_fundamentals

FAKE_INFO = {
    "shortName": "Example Corp",
    "totalRevenue": 1_000_000_000,
    "netIncomeToCommon": 200_000_000,
    "grossMargins": 0.5,
    "operatingMargins": 0.3,
    "profitMargins": 0.2,
    "totalDebt": 400_000_000,
    "debtToEquity": 80.0,
    "revenueGrowth": 0.15,
    "earningsGrowth": 0.25,
    "trailingPE": 30.0,
    "forwardPE": 25.0,
    "enterpriseToEbitda": 20.0,
    "priceToSalesTrailing12Months": 8.0,
}


class FakeTicker:
    def __init__(self, symbol):
        self.info = FAKE_INFO if symbol == "EXMP" else {}


def test_fetch_fundamentals_maps_fields(monkeypatch):
    monkeypatch.setattr("portfolio_intelligence.data.yahoo_client.yf.Ticker", FakeTicker)

    data = fetch_fundamentals(["EXMP"])

    assert list(data.index) == ["EXMP"]
    row = data.loc["EXMP"]
    assert row["name"] == "Example Corp"
    assert row["revenue"] == 1_000_000_000
    assert row["net_margin"] == 0.2
    assert row["total_debt"] == 400_000_000
    assert row["revenue_growth"] == 0.15
    assert row["pe"] == 30.0
    assert row["ev_ebitda"] == 20.0
    assert row["ps"] == 8.0


def test_fetch_fundamentals_skips_tickers_without_data(monkeypatch):
    monkeypatch.setattr("portfolio_intelligence.data.yahoo_client.yf.Ticker", FakeTicker)

    data = fetch_fundamentals(["EXMP", "NODATA"])

    assert list(data.index) == ["EXMP"]


def test_fetch_fundamentals_all_missing_raises(monkeypatch):
    monkeypatch.setattr("portfolio_intelligence.data.yahoo_client.yf.Ticker", FakeTicker)

    with pytest.raises(ValueError, match="NODATA"):
        fetch_fundamentals(["NODATA"])


def test_fetch_fundamentals_uses_fallback_when_yahoo_has_no_data(monkeypatch):
    """Su Streamlit Cloud Yahoo è bloccato: lo snapshot copre i ticker mancanti."""
    monkeypatch.setattr("portfolio_intelligence.data.yahoo_client.yf.Ticker", FakeTicker)
    monkeypatch.setattr(valuation, "_RETRY_DELAY", 0)
    fallback = pd.DataFrame({"name": ["Snapshot Inc."], "pe": [18.0]}, index=["NODATA"])

    data = fetch_fundamentals(["EXMP", "NODATA"], fallback=fallback)

    assert list(data.index) == ["EXMP", "NODATA"]
    assert data.loc["EXMP", "name"] == "Example Corp"  # il dato live ha la precedenza
    assert data.loc["NODATA", "name"] == "Snapshot Inc."
    assert data.loc["NODATA", "pe"] == 18.0
    assert pd.isna(data.loc["NODATA", "revenue"])


def test_fetch_fundamentals_retries_once_after_an_error(monkeypatch):
    calls = {"n": 0}

    class FlakyTicker:
        def __init__(self, symbol):
            calls["n"] += 1
            if calls["n"] == 1:
                raise ConnectionError("429 Too Many Requests")
            self.info = FAKE_INFO

    monkeypatch.setattr("portfolio_intelligence.data.yahoo_client.yf.Ticker", FlakyTicker)
    monkeypatch.setattr(valuation, "_RETRY_DELAY", 0)

    data = fetch_fundamentals(["EXMP"])

    assert list(data.index) == ["EXMP"]
    assert calls["n"] == 2


def test_empty_fundamentals_has_all_columns_and_no_data():
    data = empty_fundamentals(["AAPL", "MSFT"])

    assert list(data.index) == ["AAPL", "MSFT"]
    assert list(data.columns) == valuation.FUNDAMENTAL_COLUMNS
    assert data.isna().all().all()


def test_primary_source_wins_and_yahoo_only_covers_the_rest(monkeypatch):
    """Ordine: fonte primaria (SEC) → Yahoo per i mancanti → snapshot."""
    calls = []

    class CountingTicker(FakeTicker):
        def __init__(self, symbol):
            calls.append(symbol)
            super().__init__(symbol)

    monkeypatch.setattr("portfolio_intelligence.data.yahoo_client.yf.Ticker", CountingTicker)
    monkeypatch.setattr(valuation, "_RETRY_DELAY", 0)
    primary_row = {"name": "From SEC", "revenue": 5.0, "source": "SEC EDGAR"}

    data = fetch_fundamentals(["SECCO", "EXMP"], primary=lambda tks: {"SECCO": primary_row})

    assert data.loc["SECCO", "name"] == "From SEC"
    assert data.loc["SECCO", "source"] == "SEC EDGAR"
    assert data.loc["EXMP", "source"] == "Yahoo Finance"
    assert "SECCO" not in calls  # Yahoo non viene interrogato per chi ha già i dati


def test_primary_failure_does_not_block_and_yahoo_can_be_switched_off(monkeypatch):
    monkeypatch.setattr("portfolio_intelligence.data.yahoo_client.yf.Ticker", FakeTicker)

    def broken(_tickers):
        raise RuntimeError("SEC down")

    data = fetch_fundamentals(["EXMP"], primary=broken)
    assert list(data.index) == ["EXMP"]

    with pytest.raises(ValueError):
        fetch_fundamentals(["EXMP"], primary=broken, use_yahoo=False)


# ------------------------------------------------------------ cache per ticker


class _Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def _fetcher(available: dict[str, dict], calls: list):
    def fetch(tickers):
        calls.append(list(tickers))
        rows = {tk: available[tk] for tk in tickers if tk in available}
        if not rows:
            raise ValueError("no data")
        return pd.DataFrame.from_dict(rows, orient="index")

    return fetch


def test_cache_fetches_only_new_tickers():
    from portfolio_intelligence.fundamentals.valuation import FundamentalsCache

    calls: list = []
    cache = FundamentalsCache(clock=_Clock())
    data = {"AAA": {"pe": 10.0, "sector": "Technology"}, "BBB": {"pe": 20.0}, "CCC": {"pe": 30.0}}
    fetch = _fetcher(data, calls)
    cache.get(["AAA", "BBB"], fetch)
    frame = cache.get(["AAA", "BBB", "CCC"], fetch)
    assert calls == [["AAA", "BBB"], ["CCC"]]  # aggiungere un titolo non riscarica gli altri
    assert list(frame.index) == ["AAA", "BBB", "CCC"]
    assert frame.loc["CCC", "pe"] == 30.0
    assert frame["pe"].dtype.kind == "f"


def test_cache_remembers_tickers_without_data():
    from portfolio_intelligence.fundamentals.valuation import FundamentalsCache

    calls: list = []
    clock = _Clock()
    cache = FundamentalsCache(clock=clock, negative_ttl=600)
    fetch = _fetcher({}, calls)
    for _ in range(3):  # portafoglio di soli ETF: una sola richiesta, non una per interazione
        with pytest.raises(ValueError):
            cache.get(["QQQ", "SPY"], fetch)
    assert calls == [["QQQ", "SPY"]]
    clock.now = 601  # il "nessun dato" scade prima: una fonte tornata disponibile viene riletta
    with pytest.raises(ValueError):
        cache.get(["QQQ", "SPY"], fetch)
    assert len(calls) == 2


def test_cache_expires_and_stays_bounded():
    from portfolio_intelligence.fundamentals.valuation import FundamentalsCache

    calls: list = []
    clock = _Clock()
    cache = FundamentalsCache(clock=clock, ttl=3600, max_entries=2)
    fetch = _fetcher({"AAA": {"pe": 1.0}, "BBB": {"pe": 2.0}, "CCC": {"pe": 3.0}}, calls)
    cache.get(["AAA"], fetch)
    clock.now = 3601
    cache.get(["AAA"], fetch)
    assert calls == [["AAA"], ["AAA"]]
    clock.now = 3602
    cache.get(["BBB"], fetch)
    clock.now = 3603
    cache.get(["CCC"], fetch)
    assert len(cache._entries) == 2 and "AAA" not in cache._entries
