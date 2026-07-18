"""Selezione su option chain: scadenza, strike e mid sono scelti bene (senza rete)."""

import pandas as pd
import pytest

from src.data.options_chain import days_to, mid_price, nearest_expiry, nearest_strike_row

TODAY = "2026-07-17"


def test_nearest_expiry_picks_closest_future_date():
    expiries = ["2026-07-24", "2026-08-21", "2026-10-16", "2027-01-15"]
    assert nearest_expiry(expiries, 90, today=TODAY) == "2026-10-16"
    assert nearest_expiry(expiries, 7, today=TODAY) == "2026-07-24"


def test_nearest_expiry_skips_past_dates_and_handles_empty():
    assert nearest_expiry(["2026-07-10"], 30, today=TODAY) is None  # già scaduta
    assert nearest_expiry([], 30, today=TODAY) is None


def test_days_to():
    assert days_to("2026-10-15", today=TODAY) == 90


def test_nearest_strike_row():
    table = pd.DataFrame({"strike": [300.0, 310.0, 320.0], "bid": [1, 2, 3], "ask": [2, 3, 4]})
    row = nearest_strike_row(table, 313.0)
    assert row["strike"] == 310.0
    assert nearest_strike_row(pd.DataFrame(), 313.0) is None


def test_mid_price_prefers_book_then_last_trade():
    assert mid_price(pd.Series({"bid": 7.9, "ask": 8.3, "lastPrice": 5.0})) == pytest.approx(8.1)
    assert mid_price(pd.Series({"bid": 0.0, "ask": 0.0, "lastPrice": 5.0})) == 5.0
    assert mid_price(pd.Series({"bid": 0.0, "ask": 0.0, "lastPrice": 0.0})) is None
