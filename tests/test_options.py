"""Black-Scholes e strategie di overlay: valori noti e coerenza interna."""

import pytest

from src.analytics.options import (
    bs_price,
    covered_call,
    income_table,
    protection_table,
    protective_put,
    zero_cost_collar,
)


def test_black_scholes_matches_textbook_values():
    # caso classico: S=100, K=100, T=1, sigma=20%, r=5%
    assert bs_price("call", 100, 100, 1.0, 0.20, 0.05) == pytest.approx(10.4506, abs=1e-3)
    assert bs_price("put", 100, 100, 1.0, 0.20, 0.05) == pytest.approx(5.5735, abs=1e-3)


def test_put_call_parity():
    from math import exp

    call = bs_price("call", 100, 95, 0.5, 0.3, 0.04)
    put = bs_price("put", 100, 95, 0.5, 0.3, 0.04)
    assert call - put == pytest.approx(100 - 95 * exp(-0.04 * 0.5), abs=1e-9)


def test_protective_put_locks_a_floor_below_spot():
    result = protective_put(200.0, sigma=0.35, strike_pct=0.95, days=90, cost_basis=150.0)
    assert result["strike"] == pytest.approx(190.0)
    assert 0 < result["premium"] < 200.0 * 0.10  # premio plausibile, non assurdo
    assert result["floor_exit"] == pytest.approx(190.0 - result["premium"])
    # carico 150 → anche nel caso peggiore il P&L resta positivo (gain bloccato)
    assert result["locked_pnl"] == pytest.approx(result["floor_exit"] - 150.0)
    assert result["locked_pnl"] > 0


def test_covered_call_yield_is_premium_over_spot():
    result = covered_call(200.0, sigma=0.35, strike_pct=1.05, days=90)
    assert result["cap"] == pytest.approx(210.0)
    assert result["yield_pct"] == pytest.approx(result["premium"] / 200.0)
    assert result["premium"] > 0


def test_zero_cost_collar_call_finances_the_put():
    result = zero_cost_collar(200.0, sigma=0.35, put_strike_pct=0.95, days=90)
    assert result["floor"] == pytest.approx(190.0)
    assert result["cap"] > 200.0  # la call venduta è out of the money
    assert abs(result["premium_net"]) < 0.05  # premio netto ~zero per costruzione


def test_invalid_inputs_raise():
    with pytest.raises(ValueError):
        bs_price("call", 100, 100, 0.0, 0.2)
    with pytest.raises(ValueError):
        bs_price("straddle", 100, 100, 1.0, 0.2)


def _chain():
    import pandas as pd

    return pd.DataFrame(
        {
            "strike": [280.0, 300.0, 315.0, 335.0, 350.0, 370.0, 400.0],
            "bid": [2.0, 4.0, 10.35, 15.0, 12.85, 8.0, 3.0],
            "ask": [2.4, 4.4, 10.65, 15.5, 13.30, 8.5, 3.4],
            "lastPrice": [2.2, 4.1, 10.39, 15.2, 13.12, 8.2, 3.1],
            "impliedVolatility": [0.32, 0.30, 0.29, 0.28, 0.30, 0.31, 0.33],
            "openInterest": [100, 500, 2406, 800, 5890, 1200, 300],
        }
    )


def test_protection_table_facts_with_locked_pnl():
    table = protection_table(_chain(), spot=334.0, days=90, cost_basis=150.0, qty=20, fx=0.9)
    # solo strike tra 80% e 100% dello spot: 280, 300, 315, (335 escluso: >100.1%)
    assert list(table["strike"]) == [315.0, 300.0, 280.0]
    row = table.iloc[0]
    assert row["mid"] == pytest.approx(10.5)
    assert row["floor"] == pytest.approx(315.0 - 10.5)
    # P&L bloccato: (floor - carico) × qty × fx
    assert row["locked_pnl"] == pytest.approx((304.5 - 150.0) * 20 * 0.9)
    assert row["oi"] == 2406


def test_income_table_yields_annualized():
    table = income_table(_chain(), spot=334.0, days=90, qty=20, fx=0.9)
    # strike da ~100% a 120% dello spot: 335, 350, 370 e 400 (=119.8%)
    assert list(table["strike"]) == [335.0, 350.0, 370.0, 400.0]
    row = table[table["strike"] == 350.0].iloc[0]
    assert row["mid"] == pytest.approx((12.85 + 13.30) / 2)
    assert row["yield_ann"] == pytest.approx(row["yield_pct"] * 365 / 90)
    assert row["income"] == pytest.approx(row["mid"] * 20 * 0.9)


def test_tables_empty_on_empty_chain():
    import pandas as pd

    assert protection_table(pd.DataFrame(), 100.0, 90).empty
    assert income_table(None, 100.0, 90).empty
