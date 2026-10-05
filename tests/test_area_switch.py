"""Selettore d'area Investor | Advisor: cambio nella stessa sessione, stato separato."""

from streamlit.testing.v1 import AppTest


def _investor_header():
    import streamlit as st

    from portfolio_intelligence.ui.area_switch import area_switch

    st.session_state.setdefault("positions", {})
    area_switch("investor", "area_sw_test")


def test_switch_is_hidden_without_the_router():
    at = AppTest.from_function(_investor_header).run()
    assert not at.get("button_group")


def test_switching_area_keeps_each_area_portfolio_separate():
    at = AppTest.from_function(_investor_header)
    at.session_state["area_router"] = True
    at.session_state["positions"] = {"AAPL": 1000.0}  # lavoro in corso nell'area Investor
    at.session_state["area_positions_advisor"] = {"MSFT": 500.0}  # cliente aperto in Advisor
    at.run()

    at.button_group[0].set_value("advisor").run()

    assert at.query_params["profile"] == ["advisor"]
    assert at.session_state["positions"] == {"MSFT": 500.0}
    assert at.session_state["area_positions_investor"] == {"AAPL": 1000.0}


def test_clicking_the_active_area_does_nothing():
    at = AppTest.from_function(_investor_header)
    at.session_state["area_router"] = True
    at.session_state["positions"] = {"AAPL": 1000.0}
    at.run()

    at.button_group[0].set_value(None).run()

    assert "profile" not in at.query_params
    assert at.session_state["positions"] == {"AAPL": 1000.0}
    assert at.session_state["area_sw_test"] == "investor"


def test_router_enables_the_switch_only_without_a_fixed_app_mode():
    with open("app.py") as f:
        source = f.read()
    assert 'st.session_state[ROUTER_FLAG] = _MODE not in ("investor", "advisor")' in source
