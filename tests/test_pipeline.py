"""La pipeline condivisa produce un quadro coerente da prezzi sintetici."""

import numpy as np
import pandas as pd
import pytest

from src.analytics.pipeline import analyze_portfolio

RNG = np.random.default_rng(21)
DAYS = 260
INDEX = pd.bdate_range("2025-01-02", periods=DAYS)


def _prices(cols: dict[str, float]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            name: 100 * (1 + pd.Series(RNG.normal(drift, 0.012, DAYS), index=INDEX)).cumprod()
            for name, drift in cols.items()
        }
    )


PRICES = _prices({"AAA": 0.0006, "BBB": 0.0003, "CCC": 0.0004})
BENCH = _prices({"QQQ": 0.0005})
PORTFOLIO = [
    {"ticker": "AAA", "weight": 0.5},
    {"ticker": "BBB", "weight": 0.3},
    {"ticker": "CCC", "weight": 0.2},
]
FUND = pd.DataFrame(
    float("nan"),
    index=["AAA", "BBB", "CCC"],
    columns=["revenue_growth", "net_margin", "debt_to_equity", "pe", "ps"],
)


@pytest.fixture(scope="module")
def computed() -> dict:
    return analyze_portfolio(PRICES, BENCH, PORTFOLIO, FUND, benchmark="QQQ")


def test_pipeline_returns_all_view_keys(computed):
    expected = {
        "returns", "prices", "pf_daily", "pf_value", "bench_daily", "annual_ret",
        "annual_vol", "drawdown", "avg_corr", "var_95", "beta", "alpha",
        "min_periods", "cum_return", "risk_score", "contributions", "radar",
        "fund", "dna", "health", "breakdown", "usd_weight",
    }
    assert expected <= set(computed)


def test_cumulative_return_matches_equity_curve(computed):
    assert computed["cum_return"] == pytest.approx(
        float(computed["pf_value"].iloc[-1]) - 1
    )


def test_risk_contributions_sum_to_one(computed):
    assert float(computed["contributions"].sum()) == pytest.approx(1.0)


def test_health_and_risk_scores_bounded(computed):
    assert 0 <= computed["health"] <= 100
    assert 0 <= computed["risk_score"] <= 100


def test_drawdown_and_var_negative(computed):
    assert computed["drawdown"] <= 0
    assert computed["var_95"] < 0


def test_matches_app_conventions(computed):
    # volatilità annualizzata con radice di 252, come nel resto dell'app
    manual_vol = float(computed["pf_daily"].std()) * 252**0.5
    assert computed["annual_vol"] == pytest.approx(manual_vol, rel=0.02)
