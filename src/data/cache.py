"""Persistenza locale dei dati scaricati (CSV in data/)."""

from pathlib import Path

import pandas as pd

NASDAQ100_PRICES = Path("data/nasdaq100_prices.csv")


def save_nasdaq100_prices(prices: pd.DataFrame) -> None:
    NASDAQ100_PRICES.parent.mkdir(parents=True, exist_ok=True)
    prices.to_csv(NASDAQ100_PRICES)


def load_nasdaq100_prices() -> pd.DataFrame | None:
    if not NASDAQ100_PRICES.exists():
        return None
    return pd.read_csv(NASDAQ100_PRICES, index_col=0, parse_dates=True)
