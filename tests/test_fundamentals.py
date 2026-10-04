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
