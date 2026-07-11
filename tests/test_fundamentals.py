import pytest

from src.fundamentals.valuation import fetch_fundamentals

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
    monkeypatch.setattr("src.data.yahoo_client.yf.Ticker", FakeTicker)

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
    monkeypatch.setattr("src.data.yahoo_client.yf.Ticker", FakeTicker)

    data = fetch_fundamentals(["EXMP", "NODATA"])

    assert list(data.index) == ["EXMP"]


def test_fetch_fundamentals_all_missing_raises(monkeypatch):
    monkeypatch.setattr("src.data.yahoo_client.yf.Ticker", FakeTicker)

    with pytest.raises(ValueError, match="NODATA"):
        fetch_fundamentals(["NODATA"])
