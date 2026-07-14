import numpy as np
import pandas as pd

from src.analytics.alerts import evaluate_alerts
from src.analytics.insights import generate_suggestions, risk_contributions
from src.visualization.pdf_report import build_report

rng = np.random.default_rng(41)
RETURNS = pd.DataFrame(
    {
        "CALM": rng.normal(0.0005, 0.005, 250),
        "WILD": rng.normal(0.0005, 0.04, 250),
    }
)
PORTFOLIO = [
    {"ticker": "CALM", "weight": 0.5},
    {"ticker": "WILD", "weight": 0.5},
]


def test_alert_on_risk_concentration():
    contrib = risk_contributions(RETURNS, PORTFOLIO)
    alerts = evaluate_alerts(RETURNS, PORTFOLIO, contrib, 0.2, -0.10)
    assert any("WILD" in a and "total risk" in a for a in alerts)


def test_no_alerts_when_all_quiet():
    returns = pd.DataFrame(
        {"A": rng.normal(0.0005, 0.008, 250), "B": rng.normal(0.0005, 0.008, 250)}
    )
    # ultimo giorno tranquillo per non scattare l'alert di seduta
    returns.iloc[-1] = 0.001
    pf = [{"ticker": "A", "weight": 0.5}, {"ticker": "B", "weight": 0.5}]
    contrib = risk_contributions(returns, pf)
    alerts = evaluate_alerts(returns, pf, contrib, 0.2, -0.05)
    assert alerts == []


def test_alert_on_bad_last_session():
    returns = RETURNS.copy()
    returns.iloc[-1] = [-0.01, -0.08]  # giornata pesante trainata da WILD
    contrib = risk_contributions(returns, PORTFOLIO)
    alerts = evaluate_alerts(returns, PORTFOLIO, contrib, 0.2, -0.10)
    assert any("Last session" in a and "WILD" in a for a in alerts)


def test_generate_suggestions_flags_concentration():
    contrib = pd.Series({"WILD": 0.9, "CALM": 0.1})
    radar = {"Concentration": 80.0, "Correlation": 20.0, "Volatility": 50.0}
    suggestions = generate_suggestions({"Value": 50}, radar, contrib)
    assert any("WILD" in s for s in suggestions)


def test_build_report_produces_valid_pdf():
    pdf = build_report(
        portfolio_name="Test",
        positions={"AAPL": 4000.0, "MSFT": 3000.0},
        period="1y",
        cum_return=0.184,
        health_score=72,
        metrics={"Sharpe ratio": "1.01", "VaR 95%": "-197 €"},
        insights=["**AAPL** e **MSFT** dominano il rischio."],
        suggestions=["Diversifica su più settori."],
    )
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 1500
