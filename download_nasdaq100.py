"""Scarica lo storico dei prezzi (5 anni) di tutti i componenti del Nasdaq-100
e li salva come CSV locale in data/nasdaq100_prices.csv."""

import pandas as pd
import yfinance as yf

from src.data.cache import NASDAQ100_PRICES, save_nasdaq100_prices
from src.data.yahoo_client import get_nasdaq100_tickers

PERIOD = "5y"


def download_nasdaq100_prices() -> pd.DataFrame:
    tickers = get_nasdaq100_tickers()
    print(f"Trovati {len(tickers)} ticker Nasdaq-100, scarico {PERIOD} di storico...")

    data = yf.download(tickers, period=PERIOD, auto_adjust=True, progress=False)["Close"]

    missing = [
        ticker
        for ticker in tickers
        if ticker not in data.columns or data[ticker].isna().all()
    ]
    if missing:
        print(f"Nessun dato per {len(missing)} ticker, esclusi: {', '.join(missing)}")
        data = data.drop(columns=missing)

    return data


def main() -> None:
    prices = download_nasdaq100_prices()
    save_nasdaq100_prices(prices)
    print(f"Salvati {prices.shape[0]} giorni x {prices.shape[1]} ticker in {NASDAQ100_PRICES}")


if __name__ == "__main__":
    main()
