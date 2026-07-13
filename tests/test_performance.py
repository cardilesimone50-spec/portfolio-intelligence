import numpy as np
import pandas as pd
import pytest

from src.analytics.performance import (
    annualized_geometric_return,
    annualized_sharpe,
    beta_alpha,
    max_drawdown,
    sortino_ratio,
    value_at_risk,
)
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


def test_annualized_geometric_return_compounds():
    daily = pd.Series([0.01] * 252)
    assert annualized_geometric_return(daily) == pytest.approx(1.01**252 - 1)


def test_geometric_return_below_arithmetic_with_volatility():
    # +10% poi -10% = perdita composta; la media aritmetica direbbe zero
    daily = pd.Series([0.10, -0.10] * 50)
    geometric = annualized_geometric_return(daily)
    arithmetic = float(daily.mean()) * 252
    assert geometric < arithmetic
    assert geometric < 0


def test_max_drawdown():
    prices = pd.Series([100, 120, 90, 110])
    # picco 120 -> minimo 90 = -25%
    assert max_drawdown(prices) == pytest.approx(-0.25)


def test_max_drawdown_monotonic_rise_is_zero():
    assert max_drawdown(pd.Series([100, 110, 120])) == pytest.approx(0.0)


def test_max_drawdown_too_short_is_nan():
    result = max_drawdown(pd.Series([100.0]))
    assert result != result  # NaN


def test_sortino_greater_than_sharpe_for_asymmetric_upside():
    # tanti piccoli guadagni, poche piccole perdite: il Sortino premia
    rng = np.random.default_rng(3)
    up = rng.uniform(0.001, 0.02, 200)
    down = rng.uniform(-0.005, -0.001, 50)
    daily = np.concatenate([up, down])
    rng.shuffle(daily)
    prices = pd.DataFrame({"X": 100 * (1 + pd.Series(daily)).cumprod()})
    returns = compute_daily_returns(prices)
    pf = [{"ticker": "X", "weight": 1.0}]
    assert sortino_ratio(returns, pf) > annualized_sharpe(returns, pf)


def test_value_at_risk_is_the_5th_percentile():
    daily = pd.Series(np.linspace(-0.10, 0.09, 100))
    assert value_at_risk(daily, confidence=0.95) == pytest.approx(daily.quantile(0.05))


def test_value_at_risk_too_short_is_nan():
    result = value_at_risk(pd.Series([0.01, -0.01]))
    assert result != result  # NaN


def test_beta_of_benchmark_with_itself_is_one():
    rng = np.random.default_rng(5)
    bench = pd.Series(rng.normal(0.0005, 0.01, 300))
    beta, alpha = beta_alpha(bench, bench)
    assert beta == pytest.approx(1.0)
    assert alpha == pytest.approx(0.0, abs=1e-12)


def test_beta_of_leveraged_portfolio_is_two():
    rng = np.random.default_rng(6)
    bench = pd.Series(rng.normal(0.0005, 0.01, 300))
    beta, _ = beta_alpha(2 * bench, bench)
    assert beta == pytest.approx(2.0)


def test_alpha_positive_for_constant_extra_return():
    rng = np.random.default_rng(8)
    bench = pd.Series(rng.normal(0.0005, 0.01, 300))
    beta, alpha = beta_alpha(bench + 0.001, bench)
    assert beta == pytest.approx(1.0)
    assert alpha == pytest.approx(0.001 * 252)
