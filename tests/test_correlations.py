import numpy as np
import pandas as pd
import pytest

from src.portfolio.risk import (
    average_pairwise_correlation,
    correlation_matrix,
    correlations_with,
)

rng = np.random.default_rng(42)
_BASE = rng.normal(0, 0.01, 100)

# A e B identici (corr = 1), C opposto (corr = -1), D rumore indipendente
RETURNS = pd.DataFrame(
    {
        "A": _BASE,
        "B": _BASE,
        "C": -_BASE,
        "D": rng.normal(0, 0.01, 100),
    }
)


def test_correlation_matrix_diagonal_is_one():
    corr = correlation_matrix(RETURNS, min_periods=10)
    assert corr.loc["A", "A"] == pytest.approx(1.0)
    assert corr.loc["A", "B"] == pytest.approx(1.0)
    assert corr.loc["A", "C"] == pytest.approx(-1.0)


def test_correlations_with_sorted_and_excludes_self():
    corr = correlations_with(RETURNS, "A", min_periods=10)
    assert "A" not in corr.index
    assert corr.index[0] == "B"
    assert corr.index[-1] == "C"
    assert list(corr) == sorted(corr, reverse=True)


def test_correlations_with_unknown_ticker_raises():
    with pytest.raises(ValueError, match="ZZZ"):
        correlations_with(RETURNS, "ZZZ")


def test_correlations_with_drops_pairs_below_min_periods():
    returns = RETURNS.copy()
    returns.loc[returns.index[:95], "E"] = float("nan")
    returns.loc[returns.index[95:], "E"] = [0.01, -0.02, 0.005, 0.01, -0.01]
    corr = correlations_with(returns, "A", min_periods=40)
    assert "E" not in corr.index


def test_average_pairwise_correlation_two_identical():
    returns = RETURNS[["A", "B"]]
    assert average_pairwise_correlation(returns, min_periods=10) == pytest.approx(1.0)


def test_average_pairwise_correlation_single_ticker_is_nan():
    result = average_pairwise_correlation(RETURNS[["A"]], min_periods=10)
    assert result != result  # NaN
