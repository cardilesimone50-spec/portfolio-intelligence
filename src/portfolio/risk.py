"""Misure di rischio: volatilità e correlazioni."""

import pandas as pd

from src.portfolio import Portfolio, weights_series


def portfolio_volatility(returns: pd.DataFrame, portfolio: Portfolio) -> float:
    weights = weights_series(portfolio)
    cov_matrix = returns.cov()
    variance = weights @ cov_matrix @ weights
    return float(variance**0.5)


def correlation_matrix(returns: pd.DataFrame, min_periods: int = 40) -> pd.DataFrame:
    """Matrice di correlazione (Pearson) dei rendimenti giornalieri.

    min_periods evita correlazioni spurie tra titoli con poco storico in comune:
    le coppie sotto la soglia risultano NaN.
    """
    return returns.corr(min_periods=min_periods)


def correlations_with(
    returns: pd.DataFrame, ticker: str, min_periods: int = 40
) -> pd.Series:
    """Correlazione di ogni altro titolo con `ticker`, ordinata dalla più alta.

    Esclude il titolo stesso e le coppie senza abbastanza storico in comune.
    """
    if ticker not in returns.columns:
        raise ValueError(f"Ticker '{ticker}' non presente nei dati")
    corr = correlation_matrix(returns, min_periods=min_periods)[ticker]
    return corr.drop(index=ticker).dropna().sort_values(ascending=False)


def average_pairwise_correlation(returns: pd.DataFrame, min_periods: int = 40) -> float:
    """Correlazione media tra tutte le coppie distinte di titoli del portafoglio."""
    corr = correlation_matrix(returns, min_periods=min_periods)
    n = len(corr)
    if n < 2:
        return float("nan")
    # somma del triangolo superiore, escl. diagonale
    upper = corr.where(pd.DataFrame(
        [[i < j for j in range(n)] for i in range(n)],
        index=corr.index, columns=corr.columns,
    ))
    pairs = upper.stack()
    return float(pairs.mean()) if len(pairs) else float("nan")
