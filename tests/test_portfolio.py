from src.data.validators import weights_sum_to_one


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
