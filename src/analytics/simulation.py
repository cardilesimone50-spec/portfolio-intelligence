"""Simulatore "what if": impatto di uno shock su un titolo sul portafoglio."""

import pandas as pd

from src.portfolio import Portfolio, weights_series


def simulate_shock(
    returns: pd.DataFrame, portfolio: Portfolio, ticker: str, shock: float
) -> dict[str, float]:
    """Impatto stimato sul portafoglio se `ticker` si muove di `shock` (es. -0.20).

    - direct: solo la posizione colpita (peso × shock)
    - total: include il contagio sugli altri titoli, stimato con i beta storici
      di ciascun titolo rispetto a quello colpito
    """
    weights = weights_series(portfolio)
    if ticker not in weights.index or ticker not in returns.columns:
        raise ValueError(f"Ticker '{ticker}' non presente nel portafoglio")

    direct = float(weights[ticker] * shock)

    shocked = returns[ticker].dropna()
    variance = float(shocked.var())
    if variance == 0:
        return {"direct": direct, "total": direct}

    betas = returns[weights.index].apply(lambda col: float(col.cov(shocked))) / variance
    total = float((weights * betas).sum() * shock)
    return {"direct": direct, "total": total}
