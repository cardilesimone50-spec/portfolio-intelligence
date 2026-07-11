import pandas as pd
import pytest

from src.analytics.performance import annualized_sharpe, max_drawdown
from src.portfolio.returns import compute_daily_returns

PRICES = pd.DataFrame(
    {
        "AAPL": [100, 102, 101, 105],
        "MSFT": [200, 198, 202, 204],
    }
)

PORTFOLIO = [
    {"ticker": "AAPL", "weight": 0.5},
    {"ticker": "MSFT", "weight": 0.5},
]


def test_annualized_sharpe_positive_for_rising_portfolio():
    returns = compute_daily_returns(PRICES)
    assert annualized_sharpe(returns, PORTFOLIO) > 0


def test_annualized_sharpe_subtracts_risk_free_rate():
    returns = compute_daily_returns(PRICES)
    assert annualized_sharpe(returns, PORTFOLIO, risk_free_rate=0.03) < annualized_sharpe(
        returns, PORTFOLIO
    )


def test_max_drawdown():
    prices = pd.Series([100, 120, 90, 110])
    # picco 120 -> minimo 90 = -25%
    assert max_drawdown(prices) == pytest.approx(-0.25)


def test_max_drawdown_monotonic_rise_is_zero():
    assert max_drawdown(pd.Series([100, 110, 120])) == pytest.approx(0.0)


def test_max_drawdown_too_short_is_nan():
    result = max_drawdown(pd.Series([100.0]))
    assert result != result  # NaN
