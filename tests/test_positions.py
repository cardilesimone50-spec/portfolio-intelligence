"""Lotti con prezzo e data di carico: P&L e IRR sono onesti e verificabili."""

import pandas as pd
import pytest

from src.portfolio.positions import (
    add_lot,
    aggregate,
    cost_basis_native,
    normalize_portfolio,
    normalize_position,
    portfolio_xirr,
    position_table,
    totals,
    xirr,
)

LAST = pd.Series({"AAPL": 200.0, "MSFT": 400.0, "OLD": 50.0})
TODAY = "2026-07-17"


def test_normalize_shapes_to_lots():
    assert normalize_position(1500.0) == {"amount": 1500.0}
    single = normalize_position({"qty": 10, "price": 150})
    assert single == {"lots": [{"qty": 10.0, "price": 150.0, "date": None}]}
    dated = normalize_position({"qty": 5, "price": 100, "date": "2025-01-15"})
    assert dated["lots"][0]["date"] == "2025-01-15"
    mixed = normalize_portfolio({"aapl": {"qty": 10, "price": 150}, "OLD": 500.0})
    assert "lots" in mixed["AAPL"] and mixed["OLD"] == {"amount": 500.0}


def test_add_lot_preserves_history_and_aggregates():
    pos = add_lot(None, 10, 100, "2025-01-10")
    pos = add_lot(pos, 10, 200, "2025-06-10")
    assert len(pos["lots"]) == 2
    agg = aggregate(pos)
    assert agg["qty"] == 20.0
    assert agg["price"] == pytest.approx(150.0)
    assert agg["first_date"] == "2025-01-10"
    assert agg["all_dated"] is True
    assert cost_basis_native(pos) == pytest.approx(3000.0)


def test_position_table_computes_gain_and_holding_period():
    pos = {"AAPL": {"lots": [{"qty": 10.0, "price": 150.0, "date": "2025-07-17"}]}}
    table = position_table(pos, LAST, today=TODAY)
    row = table.loc["AAPL"]
    assert row["value"] == pytest.approx(2000.0)
    assert row["pnl"] == pytest.approx(500.0)
    assert row["days_held"] == 365
    # +33.3% in un anno esatto → IRR ≈ 33.3%
    assert row["ann_pct"] == pytest.approx(1 / 3, abs=0.01)
    assert bool(row["cost_known"]) is True


def test_position_table_applies_fx_factor_to_both_cost_and_value():
    fx = pd.Series({"AAPL": 0.9})
    pos = {"AAPL": {"qty": 10.0, "price": 150.0}}
    table = position_table(normalize_portfolio(pos), LAST, fx, today=TODAY)
    row = table.loc["AAPL"]
    assert row["value"] == pytest.approx(2000.0 * 0.9)
    assert row["cost"] == pytest.approx(1500.0 * 0.9)
    assert row["pnl_pct"] == pytest.approx(500.0 / 1500.0)


def test_legacy_amount_has_no_fake_pnl():
    table = position_table({"OLD": {"amount": 500.0}}, LAST, today=TODAY)
    row = table.loc["OLD"]
    assert row["value"] == pytest.approx(500.0)
    assert row["pnl"] != row["pnl"]  # NaN: carico non noto, niente numeri finti
    assert row["ann_pct"] != row["ann_pct"]
    assert bool(row["cost_known"]) is False


def test_totals_mixed_portfolio_flags_partial_cost():
    table = position_table(
        normalize_portfolio({"AAPL": {"qty": 10.0, "price": 150.0}, "OLD": 500.0}),
        LAST,
        today=TODAY,
    )
    agg = totals(table)
    assert agg["value"] == pytest.approx(2500.0)
    assert agg["pnl"] == pytest.approx(500.0)
    assert agg["cost_known"] is False


def test_xirr_doubling_in_one_year_is_100_percent():
    rate = xirr([("2025-07-17", -1000.0), ("2026-07-17", 2000.0)])
    assert rate == pytest.approx(1.0, abs=0.001)


def test_xirr_needs_signs_and_span():
    assert xirr([("2025-01-01", 100.0), ("2026-01-01", 200.0)]) is None  # nessun esborso
    assert xirr([("2025-01-01", -100.0), ("2025-01-03", 101.0)]) is None  # 2 giorni


def test_portfolio_xirr_requires_every_lot_dated():
    dated = {"AAPL": {"lots": [{"qty": 10.0, "price": 150.0, "date": "2025-07-17"}]}}
    undated = {"AAPL": {"lots": [{"qty": 10.0, "price": 150.0, "date": None}]}}
    rate = portfolio_xirr(dated, LAST, today=TODAY)
    assert rate == pytest.approx(1 / 3, abs=0.01)
    assert portfolio_xirr(undated, LAST, today=TODAY) is None
