"""Rappresentazione base di un portafoglio come lista di posizioni {ticker, weight}."""

from typing import TypedDict


class Position(TypedDict):
    ticker: str
    weight: float


Portfolio = list[Position]


def weights_sum_to_one(portfolio: Portfolio, tolerance: float = 1e-6) -> bool:
    total = sum(position["weight"] for position in portfolio)
    return abs(total - 1.0) <= tolerance


if __name__ == "__main__":
    example_portfolio: Portfolio = [
        {"ticker": "AAPL", "weight": 0.5},
        {"ticker": "MSFT", "weight": 0.5},
    ]
    print(weights_sum_to_one(example_portfolio))
