"""Il contesto che il router passa a ogni vista: dati e impostazioni di sessione."""

from dataclasses import dataclass, field

import pandas as pd

from portfolio_intelligence.data.benchmarks import (
    DEFAULT_BENCHMARK,
    benchmark_label,
    benchmark_name,
)
from portfolio_intelligence.portfolio import Portfolio


@dataclass
class ViewContext:
    """Tutto ciò che serve a una vista per renderizzare.

    `computed` è il dict prodotto da analyze_portfolio (None senza portafoglio).
    `pos` è la tabella posizioni (qty, carico, valore attuale, P&L) e
    `pnl_totals` i suoi totali — vedi portfolio_intelligence/portfolio/positions.py.
    `benchmark` è il ticker del benchmark contro cui è stato calcolato `computed`
    (quello salvato per il cliente nell'area Advisor, il predefinito in Investor).
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
    # False in app_investor.py: le viste non devono leggere/scrivere portafogli,
    # analisi o audit log sul DB — tutto resta in st.session_state e sparisce
    # con la sessione. True (default) per app_advisor.py.
    stateful: bool = True
    # intestazione del PDF per il cliente (nome e cognome): solo in sessione,
    # mai nel DB né nei log; vuota = nessuna intestazione nominativa
    report_recipient: str = ""
    benchmark: str = DEFAULT_BENCHMARK

    @property
    def benchmark_label(self) -> str:
        """Etichetta breve del benchmark per testi, grafici e report."""
        return benchmark_label(self.benchmark)

    @property
    def benchmark_name(self) -> str:
        """Nome esteso della serie (per gli ETF anche il fondo): metodologia dei report."""
        return benchmark_name(self.benchmark)
