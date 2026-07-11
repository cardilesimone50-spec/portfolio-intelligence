"""Unico punto di accesso alla rete: prezzi, fondamentali e lista Nasdaq-100."""

import io

import pandas as pd
import requests
import yfinance as yf

_NASDAQ100_URL = "https://www.slickcharts.com/nasdaq100"
_HEADERS = {"User-Agent": "Mozilla/5.0 (portfolio-intelligence research script)"}


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


def get_ticker_info(ticker: str) -> dict:
    """Restituisce il dizionario `info` di Yahoo Finance per un ticker."""
    return yf.Ticker(ticker).info


def get_nasdaq100_tickers() -> list[str]:
    """Scarica la lista aggiornata dei ticker che compongono il Nasdaq-100."""
    try:
        response = requests.get(_NASDAQ100_URL, headers=_HEADERS, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as exc:
        raise ValueError(
            f"Errore di rete durante il download della lista Nasdaq-100: {exc}"
        ) from exc

    tables = pd.read_html(io.StringIO(response.text))
    components = tables[0]
    return components["Symbol"].tolist()
