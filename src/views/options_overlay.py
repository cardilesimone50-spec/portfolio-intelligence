"""Vista Opzioni: proteggere i guadagni (put/collar) e generare rendita (call).

Stime teoriche Black-Scholes sulla volatilità realizzata del titolo — uno
strumento di scenario per il confronto col consulente, non una raccomandazione.
"""

import streamlit as st

from src.analytics.options import covered_call, protective_put, zero_cost_collar
from src.i18n import t
from src.ui.components import eur, sec
from src.views.common import TRADING_DAYS
from src.views.context import ViewContext


def render(ctx: ViewContext) -> None:
    c = ctx.computed
    pos = ctx.pos

    sec(t("opt.title"))
    st.markdown(t("opt.intro"))

    eligible = pos[pos["cost_known"]] if pos is not None else None
    if eligible is None or eligible.empty:
        st.info(t("opt.no_positions"))
        return

    col_pick, col_days, col_put, col_call = st.columns([2, 1.4, 1.6, 1.6], gap="large")
    with col_pick:
        ticker = st.selectbox(t("opt.pick"), list(eligible.index))
    with col_days:
        days = st.select_slider(
            t("opt.horizon"),
            options=[30, 60, 90, 180],
            value=90,
            format_func=lambda d: t("opt.days_label", days=d),
        )
    with col_put:
        put_pct = st.slider(t("opt.put_strike"), 80, 100, 95, step=1) / 100
    with col_call:
        call_pct = st.slider(t("opt.call_strike"), 100, 130, 105, step=1) / 100

    row = eligible.loc[ticker]
    spot = float(row["current_price"])
    cost = float(row["buy_price"])
    qty = float(row["qty"])
    # fattore alla valuta di visualizzazione, implicito nel valore già convertito
    fx = float(row["value"]) / (qty * spot) if qty and spot == spot else 1.0
    sigma = float(c["returns"][ticker].dropna().std()) * TRADING_DAYS**0.5
    rate = ctx.risk_free

    if not (spot == spot and sigma == sigma and sigma > 0):
        st.info(t("opt.no_positions"))
        return

    st.caption(
        t("opt.vol_used", vol=f"{sigma:.0%}", rf=f"{rate:.2%}", spot=f"{spot:,.2f}")
    )

    put = protective_put(spot, sigma, rate, strike_pct=put_pct, days=days, cost_basis=cost)
    call = covered_call(spot, sigma, rate, strike_pct=call_pct, days=days)
    collar = zero_cost_collar(
        spot, sigma, rate, put_strike_pct=put_pct, days=days, cost_basis=cost
    )

    # ---- put protettiva --------------------------------------------------
    sec(t("opt.protect_title"))
    p1, p2, p3 = st.columns(3)
    p1.metric(t("pos.buy_price"), f"{cost:,.2f}")
    p2.metric(
        t("opt.put_strike"),
        f"{put['strike']:,.2f}",
        delta=f"-{put['premium']:,.2f} premium",
        delta_color="off",
    )
    p3.metric("Floor", f"{put['floor_exit']:,.2f}")
    st.markdown(
        t(
            "opt.protect_text",
            strike=f"{put['strike']:,.2f}",
            days=days,
            premium=f"{put['premium']:,.2f}",
            pct=f"{put['premium_pct']:.1%}",
            floor=f"{put['floor_exit']:,.2f}",
        )
    )
    locked = put["locked_pnl"]
    if locked is not None:
        locked_total = locked * qty * fx
        key = "opt.locked_gain" if locked >= 0 else "opt.locked_loss"
        st.markdown(
            t(
                key,
                cost=f"{cost:,.2f}",
                pnl=f"{locked:+,.2f}",
                total=("+" if locked_total >= 0 else "") + eur(locked_total),
            )
        )

    # ---- covered call ----------------------------------------------------
    sec(t("opt.income_title"))
    period_yield = call["yield_pct"]
    st.markdown(
        t(
            "opt.income_text",
            strike=f"{call['strike']:,.2f}",
            days=days,
            premium=f"{call['premium']:,.2f}",
            yld=f"{period_yield:.2%}",
        )
        + f" (~{period_yield * 365 / days:.1%}/y · {'+' if call['premium'] >= 0 else ''}"
        + eur(call["premium"] * qty * fx)
        + ")"
    )

    # ---- collar a costo zero --------------------------------------------
    sec(t("opt.collar_title"))
    st.markdown(
        t(
            "opt.collar_text",
            cap=f"{collar['cap']:,.2f}",
            floor=f"{collar['floor']:,.2f}",
            net=f"{collar['premium_net']:+,.2f}",
        )
    )
    if collar["locked_pnl"] is not None and collar["locked_pnl"] >= 0:
        st.markdown(
            t(
                "opt.locked_gain",
                cost=f"{cost:,.2f}",
                pnl=f"{collar['locked_pnl']:+,.2f}",
                total=("+" if collar["locked_pnl"] >= 0 else "")
                + eur(collar["locked_pnl"] * qty * fx),
            )
        )

    st.caption(t("opt.disclaimer"))
