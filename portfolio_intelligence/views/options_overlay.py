"""Vista Opzioni: proteggere i guadagni (put/collar) e generare rendita (call).

Stime teoriche Black-Scholes sulla volatilità realizzata del titolo — uno
strumento di scenario per il confronto col consulente, non una raccomandazione.
"""

import streamlit as st

from portfolio_intelligence.analytics.options import (
    bs_price,
    covered_call,
    income_table,
    protection_table,
    protective_put,
    zero_cost_collar,
)
from portfolio_intelligence.data.options_chain import mid_price, nearest_strike_row
from portfolio_intelligence.formatting import missing, ui_num, ui_pct
from portfolio_intelligence.i18n import get_language, t
from portfolio_intelligence.ui.components import eur, sec, signed_eur, styled
from portfolio_intelligence.views.common import TRADING_DAYS, cached_option_chain
from portfolio_intelligence.views.context import ViewContext


def _market_check(
    chain: dict | None, kind: str, target_strike: float, spot: float, sigma: float, rate: float
) -> None:
    """Stima Black-Scholes contro la quotazione reale, a parità di contratto."""
    st.markdown(f"**{t('opt.market_title')}**")
    row = nearest_strike_row(chain["table"], target_strike) if chain else None
    mid = mid_price(row) if row is not None else None
    if chain is None or row is None or mid is None:
        st.caption(t("opt.market_unavailable"))
        return
    market_days = max(1, int(chain["days"]))
    estimate = bs_price(kind, spot, float(row["strike"]), market_days / 365.0, sigma, rate)
    diff = (mid - estimate) / estimate if estimate else float("nan")
    iv = float(row.get("impliedVolatility") or float("nan"))

    m1, m2, m3 = st.columns(3)
    m1.metric(t("opt.mkt_estimate"), ui_num(estimate, 2))
    m2.metric(
        t("opt.mkt_market"), ui_num(mid, 2), delta=ui_pct(diff, 1, signed=True), delta_color="off"
    )
    m3.metric(
        t("opt.mkt_iv"),
        ui_pct(iv, 0) if iv == iv else missing(get_language()),
        delta=f"RV {sigma:.0%}",
        delta_color="off",
    )
    oi = row.get("openInterest")
    st.caption(
        t(
            "opt.mkt_details",
            strike=ui_num(float(row["strike"]), 2),
            expiry=chain["expiry"],
            days=market_days,
            bid=ui_num(float(row.get("bid") or 0), 2),
            ask=ui_num(float(row.get("ask") or 0), 2),
            last=ui_num(float(row.get("lastPrice") or 0), 2),
            oi=ui_num(oi, 0) if oi == oi and oi is not None else missing(get_language()),
        )
    )
    if iv == iv:
        if iv > sigma * 1.1:
            verdict = t("opt.iv_higher")
        elif iv < sigma * 0.9:
            verdict = t("opt.iv_lower")
        else:
            verdict = t("opt.iv_inline")
        st.caption(t("opt.iv_note", iv=ui_pct(iv, 0), rv=ui_pct(sigma, 0), verdict=verdict))


# tabelle di confronto dei contratti: numeri nella convenzione della lingua
OPTION_TABLE_FORMAT = {
    "strike": ("num", 2),
    "strike_pct": ("pct", 1, False),
    "mid": ("num", 2),
    "cost_pct": ("pct", 2, False),
    "cost_month_pct": ("pct", 2, False),
    "floor": ("num", 2),
    "locked_pnl": ("eur", 0),
    "yield_pct": ("pct", 2, False),
    "yield_ann": ("pct", 1, False),
    "income": ("eur", 0),
    "iv": ("pct", 1, False),
    "oi": ("num", 0),
}


def render(ctx: ViewContext) -> None:
    # garantito da app.py: questa vista è dispatchata solo con un portafoglio
    # calcolato (NEEDS_PORTFOLIO); l'assert documenta l'invariante e lascia
    # mypy restringere il tipo da qui in poi.
    assert ctx.computed is not None
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

    st.caption(t("opt.vol_used", vol=ui_pct(sigma, 0), rf=ui_pct(rate, 2), spot=ui_num(spot, 2)))

    put = protective_put(spot, sigma, rate, strike_pct=put_pct, days=days, cost_basis=cost)
    call = covered_call(spot, sigma, rate, strike_pct=call_pct, days=days)
    collar = zero_cost_collar(
        spot, sigma, rate, put_strike_pct=put_pct, days=days, cost_basis=cost
    )
    put_chain = cached_option_chain(ticker, "put", days)
    call_chain = cached_option_chain(ticker, "call", days)

    # ---- put protettiva --------------------------------------------------
    sec(t("opt.protect_title"))
    p1, p2, p3 = st.columns(3)
    p1.metric(t("pos.buy_price"), ui_num(cost, 2))
    p2.metric(
        t("opt.put_strike_abs"),
        ui_num(put["strike"], 2),
        delta=t("opt.premium_delta", premium=ui_num(put["premium"], 2)),
        delta_color="off",
    )
    p3.metric(t("opt.col_floor"), ui_num(put["floor_exit"], 2))
    st.markdown(
        t(
            "opt.protect_text",
            strike=ui_num(put["strike"], 2),
            days=days,
            premium=ui_num(put["premium"], 2),
            pct=ui_pct(put["premium_pct"], 1),
            floor=ui_num(put["floor_exit"], 2),
        )
    )
    locked = put["locked_pnl"]
    if locked is not None:
        locked_total = locked * qty * fx
        key = "opt.locked_gain" if locked >= 0 else "opt.locked_loss"
        st.markdown(
            t(
                key,
                cost=ui_num(cost, 2),
                pnl=ui_num(locked, 2, signed=True),
                total=signed_eur(locked_total),
            )
        )
    _market_check(put_chain, "put", put["strike"], spot, sigma, rate)
    if put_chain is not None:
        facts = protection_table(
            put_chain["table"],
            spot,
            max(1, int(put_chain["days"])),
            cost_basis=cost,
            qty=qty,
            fx=fx,
        )
        if not facts.empty:
            with st.expander(t("opt.compare_put_title")):
                st.dataframe(
                    styled(facts, OPTION_TABLE_FORMAT),
                    column_config={
                        "strike": st.column_config.NumberColumn(t("opt.col_strike")),
                        "strike_pct": st.column_config.NumberColumn(t("opt.col_strike_pct")),
                        "mid": st.column_config.NumberColumn(t("opt.col_mid")),
                        "cost_pct": st.column_config.NumberColumn(t("opt.col_cost_pct")),
                        "cost_month_pct": st.column_config.NumberColumn(t("opt.col_cost_month")),
                        "floor": st.column_config.NumberColumn(t("opt.col_floor")),
                        "locked_pnl": st.column_config.NumberColumn(t("opt.col_locked")),
                        "iv": st.column_config.NumberColumn(t("opt.col_iv")),
                        "oi": st.column_config.NumberColumn(t("opt.col_oi")),
                    },
                    hide_index=True,
                    width="stretch",
                )
                st.caption(t("opt.compare_caption"))

    # ---- covered call ----------------------------------------------------
    sec(t("opt.income_title"))
    period_yield = call["yield_pct"]
    st.markdown(
        t(
            "opt.income_text",
            strike=ui_num(call["strike"], 2),
            days=days,
            premium=ui_num(call["premium"], 2),
            yld=ui_pct(period_yield, 2),
        )
        + " "
        + t(
            "opt.income_annual",
            ann=ui_pct(period_yield * 365 / days, 1),
            total=signed_eur(call["premium"] * qty * fx),
        )
    )
    _market_check(call_chain, "call", call["strike"], spot, sigma, rate)
    if call_chain is not None:
        facts = income_table(
            call_chain["table"], spot, max(1, int(call_chain["days"])), qty=qty, fx=fx
        )
        if not facts.empty:
            with st.expander(t("opt.compare_call_title")):
                st.dataframe(
                    styled(facts, OPTION_TABLE_FORMAT),
                    column_config={
                        "strike": st.column_config.NumberColumn(t("opt.col_strike")),
                        "strike_pct": st.column_config.NumberColumn(t("opt.col_strike_pct")),
                        "mid": st.column_config.NumberColumn(t("opt.col_mid")),
                        "yield_pct": st.column_config.NumberColumn(t("opt.col_yield")),
                        "yield_ann": st.column_config.NumberColumn(t("opt.col_yield_ann")),
                        "income": st.column_config.NumberColumn(t("opt.col_income")),
                        "iv": st.column_config.NumberColumn(t("opt.col_iv")),
                        "oi": st.column_config.NumberColumn(t("opt.col_oi")),
                    },
                    hide_index=True,
                    width="stretch",
                )
                st.caption(t("opt.compare_caption"))

    # ---- collar a costo zero --------------------------------------------
    sec(t("opt.collar_title"))
    st.markdown(
        t(
            "opt.collar_text",
            cap=ui_num(collar["cap"], 2),
            floor=ui_num(collar["floor"], 2),
            net=ui_num(collar["premium_net"], 2, signed=True),
        )
    )
    if collar["locked_pnl"] is not None and collar["locked_pnl"] >= 0:
        st.markdown(
            t(
                "opt.locked_gain",
                cost=ui_num(cost, 2),
                pnl=ui_num(collar["locked_pnl"], 2, signed=True),
                total=("+" if collar["locked_pnl"] >= 0 else "")
                + eur(collar["locked_pnl"] * qty * fx),
            )
        )

    st.caption(t("opt.disclaimer"))
