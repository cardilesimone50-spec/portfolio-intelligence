"""Fondamentali di bilancio e multipli di valutazione."""

import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

from portfolio_intelligence.data.yahoo_client import get_ticker_info
from portfolio_intelligence.logging_config import get_logger

log = get_logger(__name__)

# Campo yfinance -> nome colonna del report
_FIELDS = {
    "shortName": "name",
    "sector": "sector",
    "dividendYield": "dividend_yield",  # in punti percentuali (2.5 = 2.5%)
    "totalRevenue": "revenue",
    "netIncomeToCommon": "net_income",
    "grossMargins": "gross_margin",
    "operatingMargins": "operating_margin",
    "profitMargins": "net_margin",
    "totalDebt": "total_debt",
    "debtToEquity": "debt_to_equity",
    "revenueGrowth": "revenue_growth",
    "earningsGrowth": "earnings_growth",
    "trailingPE": "pe",
    "forwardPE": "forward_pe",
    "enterpriseToEbitda": "ev_ebitda",
    "priceToSalesTrailing12Months": "ps",
}
FUNDAMENTAL_COLUMNS = list(_FIELDS.values())
YAHOO_SOURCE = "Yahoo Finance"

_ATTEMPTS = 2  # Yahoo risponde a singhiozzo (rate limit): un secondo tentativo basta quasi sempre
_RETRY_DELAY = 0.8


def _fetch_info(ticker: str) -> dict | None:
    """`info` di Yahoo con un nuovo tentativo su errore o risposta vuota."""
    for attempt in range(_ATTEMPTS):
        try:
            info = get_ticker_info(ticker)
        except Exception:
            info = None
        if info:
            return info
        if attempt < _ATTEMPTS - 1:
            time.sleep(_RETRY_DELAY)
    return None


def fetch_fundamentals(
    tickers: list[str],
    fallback: pd.DataFrame | None = None,
    primary: Callable[[list[str]], dict[str, dict]] | None = None,
    use_yahoo: bool = True,
) -> pd.DataFrame:
    """Scarica i fondamentali per una lista di ticker, una riga per ticker.

    Ordine delle fonti: `primary` (es. SEC EDGAR, dati pubblici riutilizzabili),
    poi Yahoo per i ticker rimasti (se `use_yahoo`), poi `fallback` (es. lo
    snapshot Nasdaq-100 spedito col deploy). La colonna `source` dice da dove
    arriva ogni riga. I ticker senza dati vengono esclusi; se nessun ticker ha
    dati solleva ValueError. I campi assenti per un singolo ticker restano NaN.
    """
    rows: dict[str, dict] = {}
    if primary is not None:
        try:
            rows.update(primary(tickers))
        except Exception as exc:  # noqa: BLE001 — la fonte primaria non deve bloccare
            log.warning("Primary fundamentals source failed: %s", exc)

    missing = [t for t in tickers if t not in rows]
    if use_yahoo and missing:
        # una richiesta HTTP per ticker: in parallelo il tempo diventa ~costante
        with ThreadPoolExecutor(max_workers=8) as executor:
            for ticker, info in zip(missing, executor.map(_fetch_info, missing), strict=True):
                if not info or info.get("totalRevenue") is None:
                    continue
                rows[ticker] = {column: info.get(field) for field, column in _FIELDS.items()}
                rows[ticker]["source"] = YAHOO_SOURCE

    if fallback is not None:
        for ticker in tickers:
            if ticker not in rows and ticker in fallback.index:
                rows[ticker] = (
                    fallback.loc[ticker].reindex([*FUNDAMENTAL_COLUMNS, "source"]).to_dict()
                )

    if not rows:
        raise ValueError(f"No fundamental data found for: {', '.join(tickers)}")

    return pd.DataFrame.from_dict(rows, orient="index")


def empty_fundamentals(tickers: list[str]) -> pd.DataFrame:
    """Tabella fondamentali tutta NaN: l'analisi prosegue senza bilanci."""
    return pd.DataFrame(index=pd.Index(tickers), columns=FUNDAMENTAL_COLUMNS, dtype=object)
