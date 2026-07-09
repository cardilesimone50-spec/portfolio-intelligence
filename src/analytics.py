"""Calcolo di rendimento e rischio di un portafoglio a partire dai prezzi storici."""

import pandas as pd

from src.portfolio import Portfolio


def compute_daily_returns(prices: pd.DataFrame) -> pd.DataFrame:
    return prices.pct_change().dropna()


def _weights_series(portfolio: Portfolio) -> pd.Series:
    return pd.Series({position["ticker"]: position["weight"] for position in portfolio})


def portfolio_expected_return(returns: pd.DataFrame, portfolio: Portfolio) -> float:
    weights = _weights_series(portfolio)
    mean_returns = returns.mean()
    return float((mean_returns * weights).sum())


def portfolio_volatility(returns: pd.DataFrame, portfolio: Portfolio) -> float:
    weights = _weights_series(portfolio)
    cov_matrix = returns.cov()
    variance = weights @ cov_matrix @ weights
    return float(variance**0.5)
