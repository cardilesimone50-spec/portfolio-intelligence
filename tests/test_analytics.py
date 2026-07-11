import pandas as pd
import pytest

from src.analytics.performance import per_ticker_annualized_stats
from src.portfolio.returns import (
    compute_daily_returns,
    per_ticker_cumulative_return,
    portfolio_expected_return,
)
from src.portfolio.risk import portfolio_volatility

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


def test_per_ticker_cumulative_return():
    result = per_ticker_cumulative_return(PRICES)
    assert result["AAPL"] == pytest.approx(105 / 100 - 1)
    assert result["MSFT"] == pytest.approx(204 / 200 - 1)


def test_per_ticker_cumulative_return_ignores_leading_nans():
    prices = pd.DataFrame({"NEW": [float("nan"), float("nan"), 10.0, 12.0]})
    result = per_ticker_cumulative_return(prices)
    assert result["NEW"] == pytest.approx(0.2)


def test_per_ticker_annualized_stats_matches_manual_calc():
    returns = compute_daily_returns(PRICES)
    stats = per_ticker_annualized_stats(returns, trading_days=252)

    assert list(stats.columns) == ["annual_return", "annual_volatility"]
    assert list(stats.index) == ["AAPL", "MSFT"]
    assert stats.loc["AAPL", "annual_return"] == returns["AAPL"].mean() * 252
    assert stats.loc["AAPL", "annual_volatility"] == returns["AAPL"].std() * 252**0.5
