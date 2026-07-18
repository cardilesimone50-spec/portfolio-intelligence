"""Il contesto che il router passa a ogni vista: dati e impostazioni di sessione."""

from dataclasses import dataclass, field

import pandas as pd

from src.portfolio import Portfolio


@dataclass
class ViewContext:
    """Tutto ciò che serve a una vista per renderizzare.

    `computed` è il dict prodotto da analyze_portfolio (None senza portafoglio).
    `pos` è la tabella posizioni (qty, carico, valore attuale, P&L) e
    `pnl_totals` i suoi totali — vedi src/portfolio/positions.py.
    """

    computed: dict | None
    amounts: dict[str, float]
    total: float
    portfolio: Portfolio
    portfolio_name: str
    period: str
    in_eur: bool
    risk_free: float
    risk_profile: str
    advisor: str
    names: dict[str, str] = field(default_factory=dict)
    pos: pd.DataFrame | None = None
    pnl_totals: dict | None = None
    irr: float | None = None
