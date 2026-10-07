"""Backtest di strategie con ribilanciamento periodico.

Limiti dichiarati: nessun costo di transazione, e l'universo Nasdaq-100 usa i
componenti ATTUALI dell'indice (survivorship bias: i titoli usciti non ci sono).
"""

from collections.abc import Callable

import pandas as pd

from portfolio_intelligence.portfolio.optimization import (
    max_sharpe_weights,
    minimum_variance_weights,
)
from portfolio_intelligence.portfolio.returns import compute_daily_returns

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
    cost_bps: float = 0.0,
) -> pd.Series:
    """Equity curve (base 100) di una strategia ribilanciata periodicamente.

    A ogni data di ribilanciamento i pesi sono calcolati SOLO sui dati
    precedenti (finestra `lookback` giorni), mai su quelli futuri.

    cost_bps: costo di transazione in basis point (20 = 0.20%) applicato al
    controvalore scambiato a ogni ribilanciamento (acquisto iniziale incluso).
    Tra due ribilanciamenti i pesi derivano con i prezzi; il turnover è la
    distanza tra i pesi derivati a fine periodo e i nuovi pesi target.
    """
    returns = compute_daily_returns(prices)
    parts = []
    previous_weights: pd.Series | None = None
    for _, segment in returns.groupby(returns.index.to_period(rebalance[0])):
        history = returns.loc[: segment.index[0] - pd.Timedelta(days=1)].tail(lookback)
        if len(history) < _MIN_HISTORY:
            continue
        weights = weight_func(history)
        if weights.empty:
            continue
        # dentro il periodo i pesi derivano con i prezzi: si compone per titolo e
        # si ribilancia solo alla data successiva (non ogni giorno)
        growth = (1 + segment[weights.index].fillna(0.0)).cumprod()
        value = growth.mul(weights).sum(axis=1) / float(weights.sum())
        segment_returns = value.pct_change()
        segment_returns.iloc[0] = value.iloc[0] - 1

        if cost_bps:
            if previous_weights is None:
                traded = float(weights.abs().sum())  # acquisto iniziale
            else:
                union = weights.index.union(previous_weights.index)
                traded = float(
                    (
                        weights.reindex(union, fill_value=0.0)
                        - previous_weights.reindex(union, fill_value=0.0)
                    )
                    .abs()
                    .sum()
                )
            segment_returns.iloc[0] -= traded * cost_bps / 10_000

        # pesi a fine periodo dopo la deriva: base del turnover al ribilanciamento
        drifted = weights * growth.iloc[-1]
        previous_weights = drifted / float(drifted.sum())
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
