import pandas as pd

from src.data.validators import safe_load_positions, validate_price_rows, weights_sum_to_one


def test_weights_sum_to_one_valid():
    portfolio = [
        {"ticker": "AAPL", "weight": 0.5},
        {"ticker": "MSFT", "weight": 0.5},
    ]
    assert weights_sum_to_one(portfolio) is True


def test_weights_sum_to_one_invalid():
    portfolio = [
        {"ticker": "AAPL", "weight": 0.5},
        {"ticker": "MSFT", "weight": 0.3},
    ]
    assert weights_sum_to_one(portfolio) is False


def test_weights_sum_to_one_within_tolerance():
    portfolio = [
        {"ticker": "AAPL", "weight": 0.3333333},
        {"ticker": "MSFT", "weight": 0.3333333},
        {"ticker": "GOOG", "weight": 0.3333334},
    ]
    assert weights_sum_to_one(portfolio) is True


def test_weights_sum_to_one_empty_portfolio():
    assert weights_sum_to_one([]) is False


def test_validate_price_rows_drops_corrupt_rows():
    long = pd.DataFrame(
        {
            "date": ["2026-01-02", "not-a-date", "2026-01-03", "2026-01-04", "2026-01-05"],
            "ticker": ["AAPL", "AAPL", "", "MSFT", "MSFT"],
            "close": [100.0, 101.0, 50.0, "oops", -5.0],
        }
    )
    clean = validate_price_rows(long)
    # solo la prima riga è valida: le altre quattro hanno data, ticker o
    # prezzo corrotti (data non parsabile, ticker vuoto, close non numerico,
    # close negativo)
    assert len(clean) == 1
    assert clean.iloc[0]["ticker"] == "AAPL"


def test_validate_price_rows_empty_input_is_noop():
    empty = pd.DataFrame(columns=["date", "ticker", "close"])
    assert validate_price_rows(empty).empty


def test_safe_load_positions_valid_json():
    assert safe_load_positions("alice", "Client A", '{"AAPL": 100.0}') == {"AAPL": 100.0}


def test_safe_load_positions_corrupt_json_returns_none():
    assert safe_load_positions("alice", "Client A", "{not valid json") is None
