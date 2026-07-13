"""Accesso alla rete: prezzi (via catena di provider), fondamentali, lista indice.

I prezzi passano dal layer `providers` (EODHD → Yahoo → Stooq): questo modulo
resta il punto d'ingresso storico per non toccare i consumatori, ma la sorgente
è pluggabile e pronta per un feed con licenza commerciale.
"""

import io

import pandas as pd
import requests
import yfinance as yf

from src.data.providers import build_default_chain

_NASDAQ100_URL = "https://www.slickcharts.com/nasdaq100"
_HEADERS = {"User-Agent": "Mozilla/5.0 (portfolio-intelligence research script)"}

# sorgente effettiva dell'ultimo download riuscito (per mostrarla nella UI)
last_price_source: str = "—"


def fetch_price_history(tickers: list[str], period: str = "1y") -> pd.DataFrame:
    """Scarica i prezzi di chiusura (adjusted) via la catena di provider dati."""
    global last_price_source
    data, source = build_default_chain().fetch(tickers, period)
    last_price_source = source

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
