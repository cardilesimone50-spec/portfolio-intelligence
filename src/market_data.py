"""Recupero dei prezzi storici da Yahoo Finance."""

import pandas as pd
import yfinance as yf


def fetch_price_history(tickers: list[str], period: str = "1y") -> pd.DataFrame:
    """Scarica i prezzi di chiusura (adjusted) per una lista di ticker."""
    data = yf.download(tickers, period=period, auto_adjust=True, progress=False)["Close"]
    if isinstance(data, pd.Series):
        data = data.to_frame(name=tickers[0])
    return data
