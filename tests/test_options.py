"""Black-Scholes e strategie di overlay: valori noti e coerenza interna."""

import pytest

from src.analytics.options import (
    bs_price,
    covered_call,
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
