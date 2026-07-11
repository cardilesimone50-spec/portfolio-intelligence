import numpy as np
import pandas as pd
import pytest

from src.analytics.insights import (
    concentration_score,
    dna_label,
    dna_scores,
    generate_insights,
    monthly_returns,
    portfolio_risk_score,
    radar_scores,
    risk_contributions,
    stock_scores,
)

rng = np.random.default_rng(11)
RETURNS = pd.DataFrame(
    {
        "CALM": rng.normal(0.0005, 0.005, 300),
        "WILD": rng.normal(0.0005, 0.03, 300),
    }
)
PORTFOLIO = [
    {"ticker": "CALM", "weight": 0.5},
    {"ticker": "WILD", "weight": 0.5},
]


def test_risk_contributions_sum_to_one_and_rank_volatile_first():
    contrib = risk_contributions(RETURNS, PORTFOLIO)
    assert contrib.sum() == pytest.approx(1.0)
    assert contrib.index[0] == "WILD"
    assert contrib["WILD"] > 0.8  # a parità di peso, quasi tutto il rischio è di WILD


def test_concentration_score_extremes():
    equal = [{"ticker": t, "weight": 0.25} for t in "ABCD"]
    assert concentration_score(equal) == pytest.approx(0.0)
    single = [{"ticker": "A", "weight": 1.0}]
    assert concentration_score(single) == 100.0
    concentrated = [{"ticker": "A", "weight": 0.9}, {"ticker": "B", "weight": 0.1}]
    assert concentration_score(concentrated) > 60


def test_radar_and_risk_score_bounds():
    radar = radar_scores(0.35, PORTFOLIO, -0.25, 0.5)
    assert set(radar) == {"Volatilità", "Concentrazione", "Drawdown", "Correlazione"}
    assert all(0 <= v <= 100 for v in radar.values())
    assert 0 <= portfolio_risk_score(radar) <= 100


def test_dna_scores_growth_portfolio():
    fund = pd.DataFrame(
        {
            "revenue_growth": [0.5, 0.4],
            "net_margin": [0.3, 0.25],
            "debt_to_equity": [20.0, 30.0],
            "pe": [55.0, 60.0],
            "ps": [15.0, 18.0],
        },
        index=["CALM", "WILD"],
    )
    dna = dna_scores(fund, PORTFOLIO, annual_volatility=0.5, avg_correlation=0.7)
    assert dna["Growth"] == 100.0  # crescita >40% satura la scala
    assert dna["Value"] < 30  # multipli carissimi
    assert dna["Risk"] >= 50
    assert "growth" in dna_label(dna).lower()


def test_stock_scores_bounds_and_overall():
    row = pd.Series(
        {
            "revenue_growth": 0.85, "earnings_growth": 2.0, "net_margin": 0.63,
            "operating_margin": 0.65, "debt_to_equity": 6.6, "pe": 31.0,
            "ps": 19.0, "ev_ebitda": 30.0,
        }
    )
    scores = stock_scores(row, annual_volatility=0.5)
    assert scores["Growth"] == 100.0
    assert scores["Quality"] > 90
    assert 0 <= scores["Valuation"] <= 100
    assert 0 <= scores["Overall"] <= 100


def test_monthly_returns_compound_correctly():
    index = pd.date_range("2026-01-01", periods=40, freq="B")
    daily = pd.Series(0.01, index=index)
    monthly = monthly_returns(daily)
    january = monthly[monthly.index.month == 1].iloc[0]
    n_january = (index.month == 1).sum()
    assert january == pytest.approx(1.01**n_january - 1)


def test_generate_insights_mentions_top_risk_contributors():
    contrib = risk_contributions(RETURNS, PORTFOLIO)
    insights = generate_insights("1y", 0.12, contrib, 0.7, -0.20, 1.3, "QQQ")
    text = " ".join(insights)
    assert "WILD" in text
    assert "+12.0%" in text
    assert "0.70" in text  # correlazione alta segnalata
