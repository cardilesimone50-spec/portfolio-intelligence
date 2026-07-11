"""Ottimizzazione dei pesi di portafoglio (long-only, somma 1)."""

import numpy as np
import pandas as pd
from scipy.optimize import minimize

TRADING_DAYS = 252


def _optimize(returns: pd.DataFrame, objective) -> pd.Series:
    n = returns.shape[1]
    result = minimize(
        objective,
        x0=np.full(n, 1 / n),
        method="SLSQP",
        bounds=[(0.0, 1.0)] * n,
        constraints=[{"type": "eq", "fun": lambda w: w.sum() - 1.0}],
        options={"ftol": 1e-12, "maxiter": 1000},
    )
    if not result.success:
        raise ValueError(f"Ottimizzazione fallita: {result.message}")
    weights = pd.Series(result.x, index=returns.columns)
    # azzera il rumore numerico dell'ottimizzatore
    weights[weights < 1e-6] = 0.0
    return weights / weights.sum()


def minimum_variance_weights(returns: pd.DataFrame) -> pd.Series:
    """Pesi che minimizzano la varianza del portafoglio."""
    # annualizzata: non cambia l'argmin ma evita che SLSQP consideri
    # "già convergente" un obiettivo dell'ordine di 1e-5
    cov = returns.cov().to_numpy() * TRADING_DAYS
    return _optimize(returns, lambda w: w @ cov @ w)


def max_sharpe_weights(returns: pd.DataFrame, risk_free_rate: float = 0.0) -> pd.Series:
    """Pesi che massimizzano lo Sharpe ratio annualizzato.

    risk_free_rate è annuale (es. 0.03 per il 3%).
    """
    mean = returns.mean().to_numpy() * TRADING_DAYS
    cov = returns.cov().to_numpy() * TRADING_DAYS

    def negative_sharpe(w: np.ndarray) -> float:
        volatility = float(np.sqrt(w @ cov @ w))
        if volatility == 0:
            return 0.0
        return -(float(w @ mean) - risk_free_rate) / volatility

    return _optimize(returns, negative_sharpe)
