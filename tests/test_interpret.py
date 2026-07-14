import pandas as pd
import pytest

from src.analytics.interpret import (
    interpret_beta,
    interpret_correlation,
    interpret_drawdown,
    interpret_sharpe,
    interpret_sortino,
    interpret_volatility,
    universe_percentile,
)


def test_universe_percentile():
    universe = pd.Series([0.1, 0.2, 0.3, 0.4, 0.5])
    assert universe_percentile(0.35, universe) == pytest.approx(0.6)
    assert universe_percentile(float("nan"), universe) != universe_percentile(
        float("nan"), universe
    )  # NaN


def test_volatility_bands_and_percentile():
    assert "conservative" in interpret_volatility(0.08)
    assert "diversified" in interpret_volatility(0.18)
    assert "Elevated" in interpret_volatility(0.30)
    universe = pd.Series([0.3, 0.4, 0.5, 0.6])
    text = interpret_volatility(0.20, universe)
    assert "100%" in text  # less volatile than all single stocks


def test_sharpe_bands_cover_all_cases():
    assert "not rewarded" in interpret_sharpe(-0.2)
    assert "Modest" in interpret_sharpe(0.3)
    assert "In line" in interpret_sharpe(0.8)
    assert "Above the historical norm" in interpret_sharpe(1.5)
    assert "rarely" in interpret_sharpe(2.5)
    assert interpret_sharpe(float("nan")) == ""


def test_sortino_asymmetry_detection():
    assert "upside" in interpret_sortino(1.5, 1.0)
    assert "downside" in interpret_sortino(0.7, 1.0)
    assert "symmetrically" in interpret_sortino(1.0, 1.0)


def test_drawdown_thresholds():
    assert "correction" in interpret_drawdown(-0.05)
    assert "bear market" in interpret_drawdown(-0.15)
    assert "discipline" in interpret_drawdown(-0.28)
    assert "Severe" in interpret_drawdown(-0.50)


def test_beta_and_correlation():
    assert "defensive" in interpret_beta(0.7, "QQQ")
    assert "in line" in interpret_beta(1.0, "QQQ")
    assert "amplify" in interpret_beta(1.4, "QQQ")
    assert "identically" in interpret_correlation(0.9)
    assert "independently" in interpret_correlation(0.2)
