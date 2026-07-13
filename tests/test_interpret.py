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
    assert "prudente" in interpret_volatility(0.08)
    assert "diversificato" in interpret_volatility(0.18)
    assert "elevate" in interpret_volatility(0.30).lower()
    universe = pd.Series([0.3, 0.4, 0.5, 0.6])
    text = interpret_volatility(0.20, universe)
    assert "100%" in text  # meno volatile di tutti i singoli titoli


def test_sharpe_bands_cover_all_cases():
    assert "non è stato remunerato" in interpret_sharpe(-0.2)
    assert "modesto" in interpret_sharpe(0.3)
    assert "In linea" in interpret_sharpe(0.8)
    assert "Sopra la norma" in interpret_sharpe(1.5)
    assert "raramente" in interpret_sharpe(2.5)
    assert interpret_sharpe(float("nan")) == ""


def test_sortino_asymmetry_detection():
    assert "verso l'alto" in interpret_sortino(1.5, 1.0)
    assert "nei ribassi" in interpret_sortino(0.7, 1.0)
    assert "simmetrico" in interpret_sortino(1.0, 1.0)


def test_drawdown_thresholds():
    assert "correzione" in interpret_drawdown(-0.05)
    assert "bear market" in interpret_drawdown(-0.15)
    assert "disciplina" in interpret_drawdown(-0.28)
    assert "severo" in interpret_drawdown(-0.50)


def test_beta_and_correlation():
    assert "difensivo" in interpret_beta(0.7, "QQQ")
    assert "insieme" in interpret_beta(1.0, "QQQ")
    assert "Amplifichi" in interpret_beta(1.4, "QQQ")
    assert "identici" in interpret_correlation(0.9)
    assert "indipendente" in interpret_correlation(0.2)
