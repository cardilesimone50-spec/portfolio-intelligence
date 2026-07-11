"""Validazione delle strutture dati di ingresso."""

from src.portfolio import Portfolio


def weights_sum_to_one(portfolio: Portfolio, tolerance: float = 1e-6) -> bool:
    total = sum(position["weight"] for position in portfolio)
    return abs(total - 1.0) <= tolerance
