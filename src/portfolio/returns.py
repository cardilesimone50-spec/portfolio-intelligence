"""Calcolo dei rendimenti a partire dai prezzi storici."""

import pandas as pd

from src.portfolio import Portfolio, weights_series


def compute_daily_returns(prices: pd.DataFrame) -> pd.DataFrame:
    # how="all": un ticker quotato da poco non deve cancellare lo storico degli altri;
    # mean/std/cov di pandas ignorano già i NaN residui per colonna.
    return prices.pct_change().dropna(how="all")


def portfolio_expected_return(returns: pd.DataFrame, portfolio: Portfolio) -> float:
    weights = weights_series(portfolio)
    mean_returns = returns.mean()
    return float((mean_returns * weights).sum())


def portfolio_daily_returns(returns: pd.DataFrame, portfolio: Portfolio) -> pd.Series:
    """Serie dei rendimenti giornalieri dell'intero portafoglio (somma pesata)."""
    weights = weights_series(portfolio)
    return returns[weights.index].mul(weights).sum(axis=1, min_count=1).dropna()


def per_ticker_cumulative_return(prices: pd.DataFrame) -> pd.Series:
    """Rendimento cumulato per ticker: ultimo prezzo valido / primo prezzo valido - 1."""

    def column_return(series: pd.Series) -> float:
        valid = series.dropna()
        if len(valid) < 2:
            return float("nan")
        return float(valid.iloc[-1] / valid.iloc[0] - 1)

    return prices.apply(column_return)
