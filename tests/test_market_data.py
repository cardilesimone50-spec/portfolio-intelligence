import pandas as pd
import pytest

from portfolio_intelligence.data import yahoo_client


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
    _, source = yahoo_client.fetch_prices_with_source(["AAPL", "MSFT"], period="5d")
    assert source == "Fake"


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


def test_chain_fills_tickers_missing_from_first_provider():
    from portfolio_intelligence.data.providers import ProviderChain

    class Partial:
        name = "First"

        def fetch(self, tickers, period):
            return pd.DataFrame({tk: [1.0, 2.0] for tk in tickers if tk != "RARE"})

    class Second:
        name = "Second"

        def fetch(self, tickers, period):
            return pd.DataFrame({tk: [3.0, 4.0] for tk in tickers})

    data, source = ProviderChain([Partial(), Second()]).fetch(["AAPL", "RARE"], "1y")
    assert set(data.columns) == {"AAPL", "RARE"}
    assert source == "First + Second"
