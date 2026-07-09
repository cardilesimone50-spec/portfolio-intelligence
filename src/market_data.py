"""Recupero dei prezzi storici da Yahoo Finance."""

import pandas as pd
import requests
import yfinance as yf


def fetch_price_history(tickers: list[str], period: str = "1y") -> pd.DataFrame:
    """Scarica i prezzi di chiusura (adjusted) per una lista di ticker."""
    try:
        data = yf.download(tickers, period=period, auto_adjust=True, progress=False)["Close"]
    except requests.exceptions.RequestException as exc:
        raise ValueError(f"Errore di rete durante il download dei prezzi: {exc}") from exc

    if isinstance(data, pd.Series):
        data = data.to_frame(name=tickers[0])

    missing = [
        ticker
        for ticker in tickers
        if ticker not in data.columns or data[ticker].isna().all()
    ]
    if missing:
        raise ValueError(f"Nessun dato trovato per i ticker: {', '.join(missing)}")

    return data
