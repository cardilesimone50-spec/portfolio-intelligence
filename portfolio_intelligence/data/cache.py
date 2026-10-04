"""Persistenza locale dei dati scaricati (CSV in data/)."""

from pathlib import Path

import pandas as pd

NASDAQ100_PRICES = Path("data/nasdaq100_prices.csv")
# fondamentali di riserva: Yahoo è bloccato sugli IP cloud, lo snapshot no
NASDAQ100_FUNDAMENTALS = Path("data/nasdaq100_fundamentals.csv")


def save_nasdaq100_prices(prices: pd.DataFrame) -> None:
    NASDAQ100_PRICES.parent.mkdir(parents=True, exist_ok=True)
    prices.to_csv(NASDAQ100_PRICES)


def load_nasdaq100_prices() -> pd.DataFrame | None:
    if not NASDAQ100_PRICES.exists():
        return None
    return pd.read_csv(NASDAQ100_PRICES, index_col=0, parse_dates=True)


def save_nasdaq100_fundamentals(fundamentals: pd.DataFrame) -> None:
    NASDAQ100_FUNDAMENTALS.parent.mkdir(parents=True, exist_ok=True)
    fundamentals.to_csv(NASDAQ100_FUNDAMENTALS, index_label="ticker")


def load_nasdaq100_fundamentals() -> pd.DataFrame | None:
    if not NASDAQ100_FUNDAMENTALS.exists():
        return None
    return pd.read_csv(NASDAQ100_FUNDAMENTALS, index_col="ticker")
