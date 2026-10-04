import pandas as pd
import pytest

from portfolio_intelligence.report import generate_report

PORTFOLIO = [
    {"ticker": "AAPL", "weight": 0.5},
    {"ticker": "MSFT", "weight": 0.5},
]


def test_generate_report_raises_on_invalid_weights():
    portfolio = [
        {"ticker": "AAPL", "weight": 0.5},
        {"ticker": "MSFT", "weight": 0.3},
    ]
    with pytest.raises(ValueError):
        generate_report(portfolio)


def test_generate_report_prints_summary(monkeypatch, capsys):
    prices = pd.DataFrame(
        {"AAPL": [100.0, 101.0, 102.0], "MSFT": [200.0, 199.0, 201.0]},
        index=pd.to_datetime(["2026-01-02", "2026-01-03", "2026-01-04"]),
    )
    monkeypatch.setattr(
        "portfolio_intelligence.report.fetch_price_history", lambda *a, **k: prices
    )

    generate_report(PORTFOLIO, period="1y")

    out = capsys.readouterr().out
    assert "Portafoglio (1y)" in out
    assert "AAPL: 50.0%" in out
    assert "Rendimento medio giornaliero atteso" in out
    assert "Volatilità giornaliera" in out


def test_generate_report_raises_when_returns_are_insufficient(monkeypatch):
    # un solo prezzo: compute_daily_returns non ha nulla su cui calcolare un ritorno
    prices = pd.DataFrame({"AAPL": [100.0], "MSFT": [200.0]}, index=pd.to_datetime(["2026-01-02"]))
    monkeypatch.setattr(
        "portfolio_intelligence.report.fetch_price_history", lambda *a, **k: prices
    )

    with pytest.raises(ValueError, match="Insufficient data"):
        generate_report(PORTFOLIO, period="1y")
