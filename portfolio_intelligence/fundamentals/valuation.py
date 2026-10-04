"""Fondamentali di bilancio e multipli di valutazione."""

import time
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

from portfolio_intelligence.data.yahoo_client import get_ticker_info

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


def fetch_fundamentals(tickers: list[str], fallback: pd.DataFrame | None = None) -> pd.DataFrame:
    """Scarica i fondamentali per una lista di ticker, una riga per ticker.

    `fallback` (es. lo snapshot Nasdaq-100 spedito col deploy) copre i ticker
    per cui Yahoo non risponde. I ticker senza dati né live né di riserva
    vengono esclusi; se nessun ticker ha dati solleva ValueError. I campi
    assenti per un singolo ticker restano NaN.
    """
    rows = {}
    # una richiesta HTTP per ticker: in parallelo il tempo diventa ~costante
    with ThreadPoolExecutor(max_workers=8) as executor:
        for ticker, info in zip(tickers, executor.map(_fetch_info, tickers), strict=True):
            if not info or info.get("totalRevenue") is None:
                continue
            rows[ticker] = {column: info.get(field) for field, column in _FIELDS.items()}

    if fallback is not None:
        for ticker in tickers:
            if ticker not in rows and ticker in fallback.index:
                rows[ticker] = fallback.loc[ticker].reindex(FUNDAMENTAL_COLUMNS).to_dict()

    if not rows:
        raise ValueError(f"No fundamental data found for: {', '.join(tickers)}")

    return pd.DataFrame.from_dict(rows, orient="index")


def empty_fundamentals(tickers: list[str]) -> pd.DataFrame:
    """Tabella fondamentali tutta NaN: l'analisi prosegue senza bilanci."""
    return pd.DataFrame(index=pd.Index(tickers), columns=FUNDAMENTAL_COLUMNS, dtype=object)
