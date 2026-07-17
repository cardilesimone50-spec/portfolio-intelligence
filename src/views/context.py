"""Il contesto che il router passa a ogni vista: dati e impostazioni di sessione."""

from dataclasses import dataclass, field

from src.portfolio import Portfolio


@dataclass
class ViewContext:
    """Tutto ciò che serve a una vista per renderizzare.

    `computed` è il dict prodotto da analyze_portfolio (None senza portafoglio).
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
