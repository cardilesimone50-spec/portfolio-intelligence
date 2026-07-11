"""Calcolo di rendimento e rischio di un portafoglio a partire dai prezzi storici."""

import pandas as pd

from src.portfolio import Portfolio


def compute_daily_returns(prices: pd.DataFrame) -> pd.DataFrame:
    # how="all": un ticker quotato da poco non deve cancellare lo storico degli altri;
    # mean/std/cov di pandas ignorano già i NaN residui per colonna.
    return prices.pct_change().dropna(how="all")


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


def per_ticker_cumulative_return(prices: pd.DataFrame) -> pd.Series:
    """Rendimento cumulato per ticker: ultimo prezzo valido / primo prezzo valido - 1."""

    def column_return(series: pd.Series) -> float:
        valid = series.dropna()
        if len(valid) < 2:
            return float("nan")
        return float(valid.iloc[-1] / valid.iloc[0] - 1)

    return prices.apply(column_return)


def per_ticker_annualized_stats(returns: pd.DataFrame, trading_days: int = 252) -> pd.DataFrame:
    """Rendimento e volatilità annualizzati per ciascun ticker, dai rendimenti giornalieri."""
    return pd.DataFrame(
        {
            "annual_return": returns.mean() * trading_days,
            "annual_volatility": returns.std() * trading_days**0.5,
        }
    )


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
