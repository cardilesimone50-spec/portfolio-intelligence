"""Tipi base del portafoglio: lista di posizioni {ticker, weight}."""

from typing import TypedDict

import pandas as pd


class Position(TypedDict):
    ticker: str
    weight: float


Portfolio = list[Position]


def weights_series(portfolio: Portfolio) -> pd.Series:
    return pd.Series({position["ticker"]: position["weight"] for position in portfolio})
