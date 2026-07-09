"""Scarica lo storico dei prezzi (5 anni) di tutti i componenti del Nasdaq-100
e li salva come CSV locale in data/nasdaq100_prices.csv."""

from pathlib import Path

import pandas as pd
import yfinance as yf

from src.nasdaq100 import get_nasdaq100_tickers

OUTPUT_PATH = Path("data/nasdaq100_prices.csv")
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
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    prices.to_csv(OUTPUT_PATH)
    print(f"Salvati {prices.shape[0]} giorni x {prices.shape[1]} ticker in {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
