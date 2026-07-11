import numpy as np
import pandas as pd
import pytest

from src.analytics.backtest import buy_and_hold, equal_weight, momentum_top, run_backtest

rng = np.random.default_rng(31)

_INDEX = pd.date_range("2024-01-01", periods=500, freq="B")
# UP cresce costantemente, FLAT è rumore a media zero
PRICES = pd.DataFrame(
    {
        "UP": 100 * (1.002 + rng.normal(0, 0.002, 500)).cumprod(),
        "FLAT": 100 * (1 + rng.normal(0, 0.01, 500)).cumprod(),
    },
    index=_INDEX,
)


def test_equal_weight_splits_evenly():
    returns = PRICES.pct_change().dropna()
    weights = equal_weight(returns)
    assert weights.sum() == pytest.approx(1.0)
    assert weights["UP"] == pytest.approx(0.5)


def test_momentum_picks_the_trending_asset():
    returns = PRICES.pct_change().dropna()
    weights = momentum_top(returns, top_n=1)
    assert list(weights.index) == ["UP"]
    assert weights["UP"] == pytest.approx(1.0)


def test_momentum_backtest_beats_equal_weight_on_persistent_trend():
    momentum_equity = run_backtest(PRICES, lambda w: momentum_top(w, top_n=1))
    equal_equity = run_backtest(PRICES, equal_weight)
    assert momentum_equity.iloc[-1] > equal_equity.iloc[-1]
    assert momentum_equity.iloc[-1] > 100


def test_backtest_insufficient_history_raises():
    short = PRICES.head(10)
    with pytest.raises(ValueError, match="insufficiente"):
        run_backtest(short, equal_weight)


def test_buy_and_hold_single_asset_tracks_price():
    weights = pd.Series({"UP": 1.0})
    equity = buy_and_hold(PRICES, weights)
    expected_final = 100 * PRICES["UP"].iloc[-1] / PRICES["UP"].iloc[0]
    assert equity.iloc[-1] == pytest.approx(expected_final)
    assert equity.iloc[0] == pytest.approx(100.0)
