import pandas as pd
import pytest

from src.data import yahoo_client


def _chain_returning(df: pd.DataFrame, source: str = "Fake"):
    class FakeChain:
        def fetch(self, tickers, period):
            return df, source

    return lambda: FakeChain()


def test_fetch_price_history_valid(monkeypatch):
    df = pd.DataFrame({"AAPL": [100, 101], "MSFT": [200, 201]})
    monkeypatch.setattr(yahoo_client, "build_default_chain", _chain_returning(df))

    result = yahoo_client.fetch_price_history(["AAPL", "MSFT"], period="5d")
    assert list(result.columns) == ["AAPL", "MSFT"]
    assert len(result) == 2
    assert yahoo_client.last_price_source == "Fake"


def test_fetch_price_history_missing_ticker_raises(monkeypatch):
    df = pd.DataFrame({"AAPL": [100, 101], "NOTATICKER": [float("nan"), float("nan")]})
    monkeypatch.setattr(yahoo_client, "build_default_chain", _chain_returning(df))

    with pytest.raises(ValueError, match="NOTATICKER"):
        yahoo_client.fetch_price_history(["AAPL", "NOTATICKER"], period="5d")


def test_fetch_price_history_all_providers_failed(monkeypatch):
    class FailingChain:
        def fetch(self, tickers, period):
            raise ValueError("No data provider responded")

    monkeypatch.setattr(yahoo_client, "build_default_chain", lambda: FailingChain())

    with pytest.raises(ValueError, match="No data provider"):
        yahoo_client.fetch_price_history(["AAPL"], period="5d")
