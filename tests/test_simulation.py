import numpy as np
import pandas as pd
import pytest

from src.analytics.simulation import simulate_shock

rng = np.random.default_rng(21)


def test_shock_on_independent_assets_is_mostly_direct():
    returns = pd.DataFrame(
        {"A": rng.normal(0, 0.01, 1000), "B": rng.normal(0, 0.01, 1000)}
    )
    pf = [{"ticker": "A", "weight": 0.5}, {"ticker": "B", "weight": 0.5}]
    impact = simulate_shock(returns, pf, "A", -0.20)
    assert impact["direct"] == pytest.approx(-0.10)
    assert impact["total"] == pytest.approx(-0.10, abs=0.02)  # contagio ~0


def test_shock_propagates_to_perfectly_correlated_twin():
    base = rng.normal(0, 0.01, 1000)
    returns = pd.DataFrame({"A": base, "B": base})
    pf = [{"ticker": "A", "weight": 0.5}, {"ticker": "B", "weight": 0.5}]
    impact = simulate_shock(returns, pf, "A", -0.20)
    assert impact["direct"] == pytest.approx(-0.10)
    assert impact["total"] == pytest.approx(-0.20)  # il gemello crolla uguale


def test_shock_unknown_ticker_raises():
    returns = pd.DataFrame({"A": rng.normal(0, 0.01, 100)})
    pf = [{"ticker": "A", "weight": 1.0}]
    with pytest.raises(ValueError, match="ZZZ"):
        simulate_shock(returns, pf, "ZZZ", -0.10)
