"""Backtest di strategie con ribilanciamento periodico.

Limiti dichiarati: nessun costo di transazione, e l'universo Nasdaq-100 usa i
componenti ATTUALI dell'indice (survivorship bias: i titoli usciti non ci sono).
"""

from typing import Callable

import pandas as pd

from src.portfolio.optimization import max_sharpe_weights, minimum_variance_weights
from src.portfolio.returns import compute_daily_returns

WeightFunc = Callable[[pd.DataFrame], pd.Series]

_MIN_HISTORY = 30  # giorni minimi di storico prima del primo ribilanciamento


def equal_weight(window_returns: pd.DataFrame) -> pd.Series:
    """Pesi uguali su tutti i titoli con abbastanza storico nella finestra."""
    valid = window_returns.columns[window_returns.notna().sum() >= _MIN_HISTORY]
    if len(valid) == 0:
        return pd.Series(dtype=float)
    return pd.Series(1 / len(valid), index=valid)


def momentum_top(window_returns: pd.DataFrame, top_n: int = 10) -> pd.Series:
    """Equipesato sui top_n titoli per rendimento cumulato nella finestra."""
    valid = window_returns.loc[:, window_returns.notna().sum() >= _MIN_HISTORY]
    if valid.shape[1] == 0:
        return pd.Series(dtype=float)
    cumulative = (1 + valid.fillna(0)).prod()
    top = cumulative.nlargest(min(top_n, len(cumulative))).index
    return pd.Series(1 / len(top), index=top)


def max_sharpe(window_returns: pd.DataFrame) -> pd.Series:
    return max_sharpe_weights(window_returns.dropna(axis=1))


def min_variance(window_returns: pd.DataFrame) -> pd.Series:
    return minimum_variance_weights(window_returns.dropna(axis=1))


def run_backtest(
    prices: pd.DataFrame,
    weight_func: WeightFunc,
    rebalance: str = "QE",
    lookback: int = 126,
) -> pd.Series:
    """Equity curve (base 100) di una strategia ribilanciata periodicamente.

    A ogni data di ribilanciamento i pesi sono calcolati SOLO sui dati
    precedenti (finestra `lookback` giorni), mai su quelli futuri.
    """
    returns = compute_daily_returns(prices)
    parts = []
    for _, segment in returns.groupby(returns.index.to_period(rebalance[0])):
        history = returns.loc[: segment.index[0] - pd.Timedelta(days=1)].tail(lookback)
        if len(history) < _MIN_HISTORY:
            continue
        weights = weight_func(history)
        if weights.empty:
            continue
        segment_returns = segment[weights.index].mul(weights).sum(axis=1, min_count=1)
        parts.append(segment_returns)

    if not parts:
        raise ValueError("Storico insufficiente per il backtest")
    daily = pd.concat(parts).dropna()
    return (1 + daily).cumprod() * 100


def buy_and_hold(prices: pd.DataFrame, weights: pd.Series) -> pd.Series:
    """Equity curve (base 100) comprando all'inizio e non toccando più nulla."""
    normalized = prices[weights.index].apply(lambda s: s / s.dropna().iloc[0])
    value = normalized.mul(weights).sum(axis=1, min_count=1) / weights.sum()
    return (value * 100).dropna()
