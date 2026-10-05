"""Metriche e testi dei report: calcoli verificabili a mano, frasi sempre basate sui dati."""

import numpy as np
import pandas as pd
import pytest

from portfolio_intelligence.analytics.report_metrics import (
    capture_ratios,
    compute_report_metrics,
    concentration,
    drawdown_episodes,
    historical_scenarios,
    stress_tests,
    weighted_multiple,
)
from portfolio_intelligence.analytics.report_narrative import (
    NOT_ASSESSED,
    investment_view,
    profile_rows,
    review_points,
    risk_level,
    risk_matrix,
)
from portfolio_intelligence.fundamentals.valuation import empty_fundamentals

# ------------------------------------------------------------------ calcoli


def test_concentration_is_herfindahl_and_its_inverse():
    hhi, effective = concentration(pd.Series({"A": 0.5, "B": 0.3, "C": 0.2}))
    assert hhi == pytest.approx(0.25 + 0.09 + 0.04)
    assert effective == pytest.approx(1 / 0.38)
    hhi_eq, eff_eq = concentration(pd.Series({k: 0.25 for k in "ABCD"}))
    assert hhi_eq == pytest.approx(0.25) and eff_eq == pytest.approx(4)


def test_weighted_pe_is_harmonic_and_ignores_losses():
    pe, coverage = weighted_multiple(
        pd.Series({"A": 0.6, "B": 0.3, "C": 0.1}), pd.Series({"A": 30.0, "B": 15.0, "C": -5.0})
    )
    assert pe == pytest.approx(0.9 / (0.6 / 30 + 0.3 / 15))  # 22.5: utili, non prezzi
    assert coverage == pytest.approx(0.9)


def test_drawdown_episodes_find_peak_trough_and_recovery():
    index = pd.bdate_range("2024-01-01", periods=9)
    value = pd.Series([100, 110, 99, 88, 105, 112, 120, 108, 115], index=index, dtype=float)
    episodes = drawdown_episodes(value)
    deepest, second = episodes[0], episodes[1]
    assert deepest.depth == pytest.approx(88 / 110 - 1)
    assert deepest.peak == index[1] and deepest.trough == index[3]
    assert deepest.recovery == index[5]  # 112 supera il massimo di 110
    assert second.depth == pytest.approx(108 / 120 - 1)
    assert second.recovery is None and second.days_to_recover is None  # ancora sotto il massimo


def test_up_and_down_capture_of_a_leveraged_copy():
    rng = np.random.default_rng(3)
    index = pd.bdate_range("2022-01-03", periods=600)
    bench = pd.Series(rng.normal(0.0004, 0.01, 600), index=index)
    up, down, basis = capture_ratios(bench * 1.5, bench)
    assert basis == "monthly"
    # sul mensile composto il rapporto non è esattamente 1,5, ma vicino
    assert up == pytest.approx(1.5, rel=0.1) and down == pytest.approx(1.5, rel=0.1)


def test_historical_scenarios_need_more_than_a_year():
    index = pd.bdate_range("2023-01-02", periods=200)
    assert historical_scenarios(pd.Series(0.001, index=index)) is None
    index = pd.bdate_range("2021-01-04", periods=600)
    scenarios = historical_scenarios(pd.Series(0.0004, index=index))
    assert scenarios is not None
    assert scenarios.bear == pytest.approx(
        (1.0004) ** 252 - 1
    )  # rendimento costante: tutte uguali
    assert scenarios.bear <= scenarios.base <= scenarios.bull
    assert scenarios.windows == 600 - 252


def _metrics(weights=None, beta_to=1.2, seed=5):
    rng = np.random.default_rng(seed)
    index = pd.bdate_range("2021-01-04", periods=800)
    bench = pd.Series(rng.normal(0.0004, 0.01, 800), index=index)
    pf = bench * beta_to + rng.normal(0.0001, 0.004, 800)
    weights = weights or {"A": 0.5, "B": 0.3, "C": 0.2}
    w = pd.Series(weights)
    risk = pd.Series({"A": 0.75, "B": 0.15, "C": 0.10})
    fund = empty_fundamentals(list(weights))
    fund["sector"] = pd.Series({"A": "Technology", "B": "Technology", "C": "Healthcare"})
    return (
        compute_report_metrics(pf, bench, w, risk, fund, usd_weight=0.9, risk_free=0.03),
        pf,
        bench,
    )


def test_report_metrics_are_consistent_with_the_series():
    m, pf, bench = _metrics()
    assert m.beta == pytest.approx(1.2, abs=0.05)
    assert m.cum_return == pytest.approx(float((1 + pf).prod() - 1))
    assert m.episodes[0].depth == pytest.approx(m.max_dd)
    assert m.sector_weights["Technology"] == pytest.approx(0.8)
    assert m.top_ticker == "A" and m.top3_weight == pytest.approx(1.0)
    assert m.risk_over_weight == ["A"]  # 75% del rischio con il 50% del capitale
    assert m.tracking_error > 0 and np.isfinite(m.information_ratio)


def test_stress_tests_cover_position_market_currency_and_history(returns_frame):
    from conftest import WEIGHTS

    weights = pd.Series(WEIGHTS)
    pf_daily = (returns_frame * weights).sum(axis=1)
    fund = empty_fundamentals(list(WEIGHTS))
    m = compute_report_metrics(
        pf_daily, returns_frame["NVDA"], weights, pd.Series(WEIGHTS), fund, usd_weight=1.0
    )
    tests = {t["key"]: t for t in stress_tests(returns_frame, weights, m, include_fx=True)}
    assert set(tests) == {"top_position", "market", "usd", "worst_month"}
    assert tests["top_position"]["direct"] == pytest.approx(-0.20 * WEIGHTS["NVDA"])
    assert tests["market"]["total"] == pytest.approx(m.beta * -0.20)
    assert tests["usd"]["direct"] == pytest.approx(-0.10)
    assert "usd" not in {
        t["key"] for t in stress_tests(returns_frame, weights, m, include_fx=False)
    }


# ------------------------------------------------------------------ testi


def test_risk_levels_follow_the_bounds():
    bounds = (0.1, 0.2, 0.3)
    assert [risk_level(v, bounds) for v in (0.05, 0.15, 0.25, 0.5)] == [
        "low",
        "moderate",
        "elevated",
        "high",
    ]
    assert risk_level(float("nan"), bounds) == NOT_ASSESSED


def test_risk_matrix_declares_liquidity_as_not_assessed():
    m, _, _ = _metrics()
    rows = {row["key"]: row for row in risk_matrix(m, in_eur=True, benchmark="QQQ", lang="en")}
    assert set(rows) == {
        "market",
        "concentration",
        "factor",
        "currency",
        "volatility",
        "drawdown",
        "liquidity",
        "valuation",
    }
    assert rows["liquidity"]["level"] == NOT_ASSESSED
    assert rows["valuation"]["level"] == NOT_ASSESSED  # nessun P/E nei dati: non si stima
    assert rows["currency"]["level"] == "high"  # 90% in dollari
    native = {r["key"]: r for r in risk_matrix(m, in_eur=False, benchmark="QQQ", lang="en")}
    assert native["currency"]["level"] == NOT_ASSESSED


def test_profile_rows_compare_against_the_benchmark():
    m, _, _ = _metrics()
    rows = {row[0]: row for row in profile_rows(m, 10_000.0, "QQQ", "en")}
    assert rows["Portfolio value"][1] == "€10,000"
    assert rows["Beta vs QQQ"][3] == "Amplifies QQQ moves"
    assert "not evidence of skill" in rows["Alpha (ann.)"][3]
    assert len(rows) == 18


def test_investment_view_statements_cite_the_data():
    m, _, _ = _metrics()
    view = dict(investment_view(m, "QQQ", "Moderate", 0.10, "en"))
    concentration_text = " ".join(view["Principal concentration"])
    assert "A represents 50.0% of capital and 75.0% of total risk" in concentration_text
    vulnerabilities = " ".join(view["Key vulnerabilities"])
    assert "A contributes 75.0% of risk on a 50.0% capital weight" in vulnerabilities
    assert "exceeds the 10% band" in vulnerabilities
    assert any(
        "not evidence of persistent skill" in s for s in view["Material investment implications"]
    )


def test_review_points_are_descriptive_and_flag_missing_profile():
    m, _, _ = _metrics()
    points = review_points(m, None, None, in_eur=True, lang="en")
    assert points[0].startswith("No risk profile declared")
    text = " ".join(points).lower()
    for word in ("buy", "sell", "should", "recommend"):
        assert word not in text, word


def test_narrative_is_translated():
    m, _, _ = _metrics()
    view = investment_view(m, "QQQ", "Moderato", 0.18, "it")
    assert view[0][0] == "Posizionamento del portafoglio"
    assert "posizioni" in view[0][1][0]
