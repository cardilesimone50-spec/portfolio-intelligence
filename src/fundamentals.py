"""Recupero dei dati fondamentali (bilancio e multipli) da Yahoo Finance."""

import pandas as pd
import yfinance as yf

# Campo yfinance -> nome colonna del report
_FIELDS = {
    "shortName": "name",
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
    rows = {}
    for ticker in tickers:
        try:
            info = yf.Ticker(ticker).info
        except Exception:
            continue
        if not info or info.get("totalRevenue") is None:
            continue
        rows[ticker] = {column: info.get(field) for field, column in _FIELDS.items()}

    if not rows:
        raise ValueError(f"Nessun dato fondamentale trovato per: {', '.join(tickers)}")

    return pd.DataFrame.from_dict(rows, orient="index")
