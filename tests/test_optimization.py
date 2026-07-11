import numpy as np
import pandas as pd
import pytest

from src.portfolio.optimization import max_sharpe_weights, minimum_variance_weights

rng = np.random.default_rng(7)

# LOW: poco volatile; HIGH: molto volatile e rendimento medio nullo;
# GOOD: volatilità media ma rendimento alto
RETURNS = pd.DataFrame(
    {
        "LOW": rng.normal(0.0002, 0.005, 500),
        "HIGH": rng.normal(0.0, 0.03, 500),
        "GOOD": rng.normal(0.002, 0.012, 500),
    }
)


def test_minimum_variance_prefers_low_volatility():
    weights = minimum_variance_weights(RETURNS)
    assert weights.sum() == pytest.approx(1.0)
    assert (weights >= 0).all()
    assert weights["LOW"] > weights["HIGH"]
    assert weights.idxmax() == "LOW"


def test_max_sharpe_prefers_high_return_per_risk():
    weights = max_sharpe_weights(RETURNS)
    assert weights.sum() == pytest.approx(1.0)
    assert (weights >= 0).all()
    assert weights.idxmax() == "GOOD"


def test_min_variance_of_independent_equal_assets_is_split():
    # due asset indipendenti a pari varianza: il minimo rischio è dividersi a metà
    returns = pd.DataFrame(
        {"A": rng.normal(0.001, 0.01, 2000), "B": rng.normal(0.001, 0.01, 2000)}
    )
    weights = minimum_variance_weights(returns)
    assert weights["A"] == pytest.approx(0.5, abs=0.05)
