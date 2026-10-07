"""Calcolo dei rendimenti a partire dai prezzi storici."""

import pandas as pd

from portfolio_intelligence.portfolio import Portfolio, weights_series


def compute_daily_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """Rendimenti giornalieri per ticker sul calendario unione delle borse.

    I buchi interni (festività di una sola borsa) sono riempiti con l'ultimo
    prezzo: il giorno di chiusura rende 0 e il movimento arriva intero il giorno
    dopo, invece di perdersi. Prima della quotazione e dopo l'ultimo prezzo
    restano NaN. how="all": un ticker quotato da poco non cancella lo storico
    degli altri; mean/std/cov di pandas ignorano i NaN residui per colonna.
    """
    inside = prices.ffill().where(prices.bfill().notna())
    return inside.pct_change(fill_method=None).dropna(how="all")


def portfolio_expected_return(returns: pd.DataFrame, portfolio: Portfolio) -> float:
    weights = weights_series(portfolio)
    mean_returns = returns.mean()
    return float((mean_returns * weights).sum())


def portfolio_daily_returns(returns: pd.DataFrame, portfolio: Portfolio) -> pd.Series:
    """Serie dei rendimenti giornalieri dell'intero portafoglio (somma pesata).

    Nei giorni in cui un titolo non ha ancora prezzi il suo peso è ripartito sui
    titoli quotati (pesi rinormalizzati), invece di contarlo come liquidità a
    rendimento zero, che sottostimerebbe volatilità e drawdown.
    """
    weights = weights_series(portfolio)
    frame = returns[weights.index]
    available = frame.notna().mul(weights).sum(axis=1)
    total = frame.mul(weights).sum(axis=1, min_count=1)
    return (total / available.where(available > 0)).dropna()


def per_ticker_cumulative_return(prices: pd.DataFrame) -> pd.Series:
    """Rendimento cumulato per ticker: ultimo prezzo valido / primo prezzo valido - 1."""

    def column_return(series: pd.Series) -> float:
        valid = series.dropna()
        if len(valid) < 2:
            return float("nan")
        return float(valid.iloc[-1] / valid.iloc[0] - 1)

    return prices.apply(column_return)
