import pandas as pd
import pytest
import requests

from src.data.yahoo_client import fetch_price_history


def test_fetch_price_history_valid(monkeypatch):
    fake_data = pd.DataFrame({"Close": {"AAPL": [100, 101], "MSFT": [200, 201]}})
    fake_close = pd.DataFrame({"AAPL": [100, 101], "MSFT": [200, 201]})

    def fake_download(tickers, period, auto_adjust, progress):
        return pd.concat({"Close": fake_close}, axis=1)

    monkeypatch.setattr("src.data.yahoo_client.yf.download", fake_download)

    result = fetch_price_history(["AAPL", "MSFT"], period="5d")
    assert list(result.columns) == ["AAPL", "MSFT"]
    assert len(result) == 2


def test_fetch_price_history_missing_ticker_raises(monkeypatch):
    fake_close = pd.DataFrame({"AAPL": [100, 101], "NOTATICKER": [float("nan"), float("nan")]})

    def fake_download(tickers, period, auto_adjust, progress):
        return pd.concat({"Close": fake_close}, axis=1)

    monkeypatch.setattr("src.data.yahoo_client.yf.download", fake_download)

    with pytest.raises(ValueError, match="NOTATICKER"):
        fetch_price_history(["AAPL", "NOTATICKER"], period="5d")


def test_fetch_price_history_network_error_raises(monkeypatch):
    def fake_download(tickers, period, auto_adjust, progress):
        raise requests.exceptions.ConnectionError("boom")

    monkeypatch.setattr("src.data.yahoo_client.yf.download", fake_download)

    with pytest.raises(ValueError, match="rete"):
        fetch_price_history(["AAPL"], period="5d")
