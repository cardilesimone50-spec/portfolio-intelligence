import numpy as np
import pandas as pd
import pytest

from src.analytics.backtest import equal_weight, run_backtest
from src.analytics.factors import (
    composite_scores,
    low_volatility,
    momentum_12_1,
    multifactor_weights,
    trend_strength,
)

rng = np.random.default_rng(51)
N = 300

RETURNS = pd.DataFrame(
    {
        # trend costante al rialzo, poca volatilità
        "STEADY": rng.normal(0.0015, 0.004, N),
        # stesso rendimento medio ma molto più volatile
        "WILD": rng.normal(0.0015, 0.035, N),
        # in discesa
        "FALLING": rng.normal(-0.002, 0.01, N),
    }
)


def test_momentum_ranks_uptrend_over_downtrend():
    momentum = momentum_12_1(RETURNS)
    assert momentum["STEADY"] > momentum["FALLING"]


def test_momentum_excludes_last_month():
    # crollo solo nell'ultimo mese: il momentum 12-1 non deve vederlo
    returns = RETURNS.copy()
    crashed = returns.copy()
    crashed.loc[crashed.index[-21:], "STEADY"] = -0.05
    assert momentum_12_1(crashed)["STEADY"] == pytest.approx(
        momentum_12_1(returns)["STEADY"]
    )


def test_low_volatility_prefers_calm():
    scores = low_volatility(RETURNS)
    assert scores["STEADY"] > scores["WILD"]


def test_trend_positive_for_rising_negative_for_falling():
    trend = trend_strength(RETURNS)
    assert trend["STEADY"] > 0
    assert trend["FALLING"] < 0


def test_composite_scores_bounds_and_ranking():
    scores = composite_scores(RETURNS)
    assert scores["pi_score"].between(0, 100).all()
    assert scores.index[0] == "STEADY"  # vince su tutti i fattori
    assert scores.index[-1] == "FALLING"


def test_multifactor_weights_selects_top_and_sums_to_one():
    weights = multifactor_weights(RETURNS, top_n=2)
    assert weights.sum() == pytest.approx(1.0)
    assert "FALLING" not in weights.index


def test_transaction_costs_reduce_equity():
    prices = pd.DataFrame(
        {
            "A": 100 * np.cumprod(1 + rng.normal(0.001, 0.01, 400)),
            "B": 100 * np.cumprod(1 + rng.normal(0.001, 0.01, 400)),
        },
        index=pd.date_range("2024-01-01", periods=400, freq="B"),
    )
    free = run_backtest(prices, equal_weight, cost_bps=0)
    costly = run_backtest(prices, equal_weight, cost_bps=50)
    assert costly.iloc[-1] < free.iloc[-1]
