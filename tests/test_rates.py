import pandas as pd
import pytest

from src.data import rates

_CHART = "src.data.providers.YahooChartProvider.fetch"


def _chart_returns(values):
    def fetch(_self, tickers, _period):
        return pd.DataFrame({tickers[0]: values})

    return fetch


def _chart_fails(_self, _tickers, _period):
    raise RuntimeError("cloud blocked")


def _download_returning(frame):
    def _fake(*_args, **_kwargs):
        return frame

    return _fake


# --- percorso primario: Yahoo chart (HTTP) ---------------------------------
def test_fetch_risk_free_from_chart_converts_percent_to_fraction(monkeypatch):
    monkeypatch.setattr(_CHART, _chart_returns([5.10, 5.25]))
    assert rates.fetch_risk_free_rate() == pytest.approx(0.0525)


def test_fetch_risk_free_rejects_implausible_value(monkeypatch):
    monkeypatch.setattr(_CHART, _chart_returns([250.0]))
    assert rates.fetch_risk_free_rate(default=0.03) == 0.03


# --- fallback: libreria yfinance quando il chart è giù ----------------------
def test_fetch_risk_free_falls_back_to_yfinance(monkeypatch):
    monkeypatch.setattr(_CHART, _chart_fails)
    monkeypatch.setattr(rates.yf, "download", _download_returning(pd.DataFrame({"Close": [4.5]})))
    assert rates.fetch_risk_free_rate() == pytest.approx(0.045)


def test_fetch_risk_free_default_when_both_sources_fail(monkeypatch):
    monkeypatch.setattr(_CHART, _chart_fails)

    def _boom(*_a, **_k):
        raise RuntimeError("network down")

    monkeypatch.setattr(rates.yf, "download", _boom)
    assert rates.fetch_risk_free_rate(default=0.025) == 0.025


def test_fetch_risk_free_default_when_both_empty(monkeypatch):
    monkeypatch.setattr(_CHART, _chart_fails)
    monkeypatch.setattr(rates.yf, "download", _download_returning(pd.DataFrame({"Close": []})))
    assert rates.fetch_risk_free_rate(default=0.02) == 0.02
