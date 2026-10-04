"""Prezzo storico alla data di acquisto: il carico si ricava, non si digita.

La chiusura RETTIFICATA del giorno d'acquisto è coerente con tutto il resto
dell'app (P&L, serie storiche): split e dividendi sono già incorporati.
Può differire leggermente dall'eseguito reale del broker — il campo prezzo
resta modificabile per chi vuole il valore esatto.
"""

import pandas as pd


def price_on_frame(
    prices: pd.DataFrame | None, ticker: str, when, max_stale_days: int = 7
) -> float | None:
    """Chiusura del giorno `when` (o ultimo giorno di borsa precedente).

    None se il ticker non è nel listino o se la data cade oltre
    `max_stale_days` dall'ultima quotazione disponibile ≤ when.
    """
    if prices is None or ticker not in getattr(prices, "columns", ()):
        return None
    series = prices[ticker].dropna()
    if series.empty:
        return None
    when = pd.Timestamp(when)
    upto = series.loc[series.index <= when]
    if upto.empty:
        return None
    last_date = upto.index[-1]
    if (when - last_date).days > max_stale_days:
        return None
    value = float(upto.iloc[-1])
    return value if value == value and value > 0 else None


def fetch_price_on(ticker: str, when) -> float | None:
    """Fallback di rete: chiusura rettificata dalla storia Yahoo del titolo."""
    try:
        import yfinance as yf

        when = pd.Timestamp(when)
        history = yf.download(
            ticker,
            start=(when - pd.Timedelta(days=10)).strftime("%Y-%m-%d"),
            end=(when + pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
            auto_adjust=True,
            progress=False,
        )
        if history is None or history.empty:
            return None
        closes = history["Close"]
        if isinstance(closes, pd.DataFrame):  # multi-index con un solo ticker
            closes = closes.iloc[:, 0]
        return price_on_frame(closes.to_frame(name=ticker), ticker, when)
    except Exception:
        return None
