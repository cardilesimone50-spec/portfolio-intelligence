import pytest

from src.report import generate_report


def test_generate_report_raises_on_invalid_weights():
    portfolio = [
        {"ticker": "AAPL", "weight": 0.5},
        {"ticker": "MSFT", "weight": 0.3},
    ]
    with pytest.raises(ValueError):
        generate_report(portfolio)
