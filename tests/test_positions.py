"""Prezzo di carico e P&L: la matematica delle posizioni è onesta."""

import pandas as pd
import pytest

from src.portfolio.positions import (
    cost_basis_native,
    normalize_portfolio,
    normalize_position,
    position_table,
    totals,
)

LAST = pd.Series({"AAPL": 200.0, "MSFT": 400.0, "OLD": 50.0})


def test_normalize_legacy_amount_and_new_shape():
    assert normalize_position(1500.0) == {"amount": 1500.0}
    assert normalize_position({"qty": 10, "price": 150}) == {"qty": 10.0, "price": 150.0}
    mixed = normalize_portfolio({"aapl": {"qty": 10, "price": 150}, "OLD": 500.0})
    assert mixed["AAPL"]["qty"] == 10.0
    assert mixed["OLD"] == {"amount": 500.0}


def test_cost_basis_native():
    assert cost_basis_native({"qty": 10.0, "price": 150.0}) == 1500.0
    assert cost_basis_native({"amount": 500.0}) is None


def test_position_table_computes_gain():
    table = position_table({"AAPL": {"qty": 10.0, "price": 150.0}}, LAST)
    row = table.loc["AAPL"]
    assert row["cost"] == pytest.approx(1500.0)
    assert row["value"] == pytest.approx(2000.0)
    assert row["pnl"] == pytest.approx(500.0)
    assert row["pnl_pct"] == pytest.approx(500.0 / 1500.0)
    assert bool(row["cost_known"]) is True


def test_position_table_applies_fx_factor_to_both_cost_and_value():
    # fattore 0.9 (es. USD→EUR): il P&L% resta il puro movimento di prezzo
    fx = pd.Series({"AAPL": 0.9})
    table = position_table({"AAPL": {"qty": 10.0, "price": 150.0}}, LAST, fx)
    row = table.loc["AAPL"]
    assert row["value"] == pytest.approx(2000.0 * 0.9)
    assert row["cost"] == pytest.approx(1500.0 * 0.9)
    assert row["pnl_pct"] == pytest.approx(500.0 / 1500.0)


def test_legacy_amount_has_no_fake_pnl():
    table = position_table({"OLD": {"amount": 500.0}}, LAST)
    row = table.loc["OLD"]
    assert row["value"] == pytest.approx(500.0)
    assert row["cost"] == pytest.approx(500.0)
    assert row["pnl"] != row["pnl"]  # NaN: carico non noto, niente numeri finti
    assert bool(row["cost_known"]) is False


def test_totals_mixed_portfolio_flags_partial_cost():
    table = position_table(
        {"AAPL": {"qty": 10.0, "price": 150.0}, "OLD": {"amount": 500.0}}, LAST
    )
    agg = totals(table)
    assert agg["value"] == pytest.approx(2500.0)
    assert agg["pnl"] == pytest.approx(500.0)  # solo la posizione con carico noto
    assert agg["pnl_pct"] == pytest.approx(500.0 / 1500.0)
    assert agg["cost_known"] is False


def test_table_sorted_by_value_desc():
    table = position_table(
        {"AAPL": {"qty": 1.0, "price": 100.0}, "MSFT": {"qty": 10.0, "price": 300.0}}, LAST
    )
    assert list(table.index) == ["MSFT", "AAPL"]
