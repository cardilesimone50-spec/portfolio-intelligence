"""Il carico dalla data: chiusura del giorno giusto, mai numeri stantii."""

import pandas as pd
import pytest

from src.data.price_lookup import price_on_frame

PRICES = pd.DataFrame(
    {"AAPL": [100.0, 102.0, 104.0, 110.0]},
    index=pd.to_datetime(["2025-03-03", "2025-03-04", "2025-03-05", "2025-03-07"]),
)


def test_exact_trading_day():
    assert price_on_frame(PRICES, "AAPL", "2025-03-04") == pytest.approx(102.0)


def test_weekend_falls_back_to_previous_close():
    # il 6 marzo manca (festivo): usa la chiusura del 5
    assert price_on_frame(PRICES, "AAPL", "2025-03-06") == pytest.approx(104.0)


def test_too_stale_returns_none():
    assert price_on_frame(PRICES, "AAPL", "2025-04-30") is None  # >7 giorni dal 07/03


def test_before_history_or_unknown_ticker_returns_none():
    assert price_on_frame(PRICES, "AAPL", "2025-03-01") is None
    assert price_on_frame(PRICES, "MSFT", "2025-03-04") is None
    assert price_on_frame(None, "AAPL", "2025-03-04") is None
