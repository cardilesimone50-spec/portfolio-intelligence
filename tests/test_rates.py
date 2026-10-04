import pandas as pd
import pytest

from portfolio_intelligence.data import rates

_CHART = "portfolio_intelligence.data.providers.YahooChartProvider.fetch"


def _chart_returns(values):
    def fetch(_self, tickers, _period):
        return pd.DataFrame({tickers[0]: values})

    return fetch


def _chart_fails(_self, _tickers, _period):
    raise RuntimeError("cloud blocked")


@pytest.fixture(autouse=True)
def _treasury_down(monkeypatch):
    """Nessuna rete nei test: il Tesoro è giù salvo override esplicito."""

    def _fail(*_a, **_k):
        raise RuntimeError("treasury unreachable")

    monkeypatch.setattr(rates, "fetch_tbill_treasury", _fail)


class _Resp:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        pass


TREASURY_CSV = (
    'Date,"4 WEEKS BANK DISCOUNT","13 WEEKS BANK DISCOUNT","13 WEEKS COUPON EQUIVALENT"\n'
    "10/02/2026,3.88,4.01,4.11\n"
    "10/01/2026,3.89,4.00,4.10\n"
)


def _download_returning(frame):
    def _fake(*_args, **_kwargs):
        return frame

    return _fake


# --- percorso primario: Tesoro USA ------------------------------------------
def test_treasury_parser_takes_latest_13_week_discount_rate(monkeypatch):
    monkeypatch.undo()  # ripristina la funzione reale, con la rete finta qui sotto
    monkeypatch.setattr(rates.requests, "get", lambda *a, **k: _Resp(TREASURY_CSV))
    assert rates.fetch_tbill_treasury() == pytest.approx(4.01)  # 10/02 è il più recente


def test_treasury_parser_falls_back_to_previous_year_when_current_is_empty(monkeypatch):
    from datetime import date

    monkeypatch.undo()
    calls = []

    def fake_get(url, **_kw):
        calls.append(url)
        return _Resp("" if "/2027/" in url else TREASURY_CSV)

    monkeypatch.setattr(rates.requests, "get", fake_get)
    assert rates.fetch_tbill_treasury(today=date(2027, 1, 2)) == pytest.approx(4.01)
    assert "/2027/" in calls[0] and "/2026/" in calls[1]


def test_treasury_is_preferred_over_yahoo(monkeypatch):
    monkeypatch.setattr(rates, "fetch_tbill_treasury", lambda: 4.01)
    monkeypatch.setattr(_CHART, _chart_returns([9.99]))  # non deve essere usato
    assert rates.fetch_risk_free_rate() == pytest.approx(0.0401)


# --- riserva: Yahoo chart (HTTP) quando il Tesoro è giù ----------------------
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
