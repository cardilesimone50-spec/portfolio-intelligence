import pandas as pd

from src.analytics import (
    compute_daily_returns,
    portfolio_expected_return,
    portfolio_volatility,
)

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


def test_compute_daily_returns_shape():
    returns = compute_daily_returns(PRICES)
    assert len(returns) == len(PRICES) - 1
    assert list(returns.columns) == ["AAPL", "MSFT"]


def test_portfolio_expected_return_matches_manual_calc():
    returns = compute_daily_returns(PRICES)
    expected = float((returns.mean() * pd.Series({"AAPL": 0.5, "MSFT": 0.5})).sum())
    assert portfolio_expected_return(returns, PORTFOLIO) == expected


def test_portfolio_volatility_is_non_negative():
    returns = compute_daily_returns(PRICES)
    volatility = portfolio_volatility(returns, PORTFOLIO)
    assert volatility >= 0
