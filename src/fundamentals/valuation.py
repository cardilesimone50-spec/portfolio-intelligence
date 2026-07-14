"""Fondamentali di bilancio e multipli di valutazione."""

from concurrent.futures import ThreadPoolExecutor

import pandas as pd

from src.data.yahoo_client import get_ticker_info

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


def fetch_fundamentals(tickers: list[str]) -> pd.DataFrame:
    """Scarica i fondamentali per una lista di ticker, una riga per ticker.

    I ticker senza dati vengono esclusi; se nessun ticker ha dati solleva ValueError.
    I campi assenti per un singolo ticker restano NaN.
    """

    def fetch_one(ticker: str) -> tuple[str, dict | None]:
        try:
            return ticker, get_ticker_info(ticker)
        except Exception:
            return ticker, None

    rows = {}
    # una richiesta HTTP per ticker: in parallelo il tempo diventa ~costante
    with ThreadPoolExecutor(max_workers=8) as executor:
        for ticker, info in executor.map(fetch_one, tickers):
            if not info or info.get("totalRevenue") is None:
                continue
            rows[ticker] = {column: info.get(field) for field, column in _FIELDS.items()}

    if not rows:
        raise ValueError(f"No fundamental data found for: {', '.join(tickers)}")

    return pd.DataFrame.from_dict(rows, orient="index")
