"""Vista Analisi (metriche): rendimento, rischio, benchmark, rolling, contributi."""

import pandas as pd
import streamlit as st

from src.analytics.interpret import (
    interpret_beta,
    interpret_drawdown,
    interpret_sharpe,
    interpret_sortino,
    interpret_volatility,
)
from src.analytics.performance import annualized_sharpe, sortino_ratio
from src.portfolio.returns import compute_daily_returns, per_ticker_cumulative_return
from src.ui.components import eur, sec
from src.views.common import BENCHMARK, TRADING_DAYS, load_market_db
from src.views.context import ViewContext
from src.visualization.charts import (
    PALETTE,
    allocation_bars,
    benchmark_overlay,
    contribution_bars,
    returns_histogram,
    simple_line,
    underwater_chart,
)


def render(ctx: ViewContext) -> None:
    c = ctx.computed
    amounts, total, portfolio = ctx.amounts, ctx.total, ctx.portfolio
    risk_free, in_eur = ctx.risk_free, ctx.in_eur

    sharpe = annualized_sharpe(c["returns"], portfolio, risk_free_rate=risk_free)
    sortino = sortino_ratio(c["returns"], portfolio, risk_free_rate=risk_free)

    # percentile di volatilità contro i singoli titoli del Nasdaq-100 (se in DB)
    _db = load_market_db()
    universe_vols = (
        compute_daily_returns(_db).std() * TRADING_DAYS**0.5 if _db is not None else None
    )

    sec("Return")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Invested", eur(total))
    m2.metric(
        "Annualized return (compound)",
        eur(total * c["annual_ret"]),
        delta=f"{c['annual_ret']:+.1%}",
        help="CAGR over the observed period: does not overstate under volatility.",
    )
    m3.metric("Sharpe ratio", f"{sharpe:.2f}", help=f"Computed with risk-free {risk_free:.1%}.")
    m3.caption(interpret_sharpe(sharpe))
    m4.metric("Sortino ratio", f"{sortino:.2f}")
    m4.caption(interpret_sortino(sortino, sharpe))

    sec("Risk")
    r1, r2, r3, r4 = st.columns(4)
    r1.metric(
        "Typical 1-year swing",
        f"± {eur(total * c['annual_vol'])}",
        delta=f"{c['annual_vol']:.1%}",
        delta_color="off",
    )
    r1.caption(interpret_volatility(c["annual_vol"], universe_vols))
    r2.metric("Max historical drop", f"{c['drawdown']:.1%}")
    r2.caption(interpret_drawdown(c["drawdown"]))
    r3.metric("95% VaR (1 day)", eur(total * c["var_95"]))
    r3.caption("On 95% of historical days you did not lose more than this.")
    r4.metric(
        f"Beta vs {BENCHMARK}",
        f"{c['beta']:.2f}",
        delta=f"α {c['alpha']:+.1%}/yr",
        delta_color="off",
    )
    r4.caption(interpret_beta(c["beta"], BENCHMARK))
    st.caption("Estimates based on historical performance: not a forecast.")

    sec(f"Portfolio vs Nasdaq-100 ({BENCHMARK}) · base 100")
    bench_value = (1 + c["bench_daily"]).cumprod()
    st.altair_chart(
        benchmark_overlay(c["pf_value"], bench_value, BENCHMARK),
        width="stretch",
    )
    excess = c["cum_return"] - float(bench_value.iloc[-1] - 1)
    st.caption(
        f"Over the period you did **{excess:+.1%}** versus the Nasdaq-100"
        + (" (net of the EUR/USD rate)." if in_eur else ".")
    )

    col_dd, col_hist = st.columns(2, gap="large")
    with col_dd:
        sec("How far below the peak (drawdown)")
        st.altair_chart(underwater_chart(c["pf_value"]), width="stretch")
        st.caption("Every dip below zero is time spent at a loss versus the prior peak.")
    with col_hist:
        sec("Distribution of days")
        st.altair_chart(returns_histogram(c["pf_daily"], c["var_95"]), width="stretch")
        st.caption(
            "Each bar counts the days with that return. The red line is the "
            "95% VaR: only 5% of days were worse."
        )

    if len(c["pf_daily"]) >= 80:
        col_rvol, col_rbeta = st.columns(2, gap="large")
        with col_rvol:
            sec("Annualized volatility · 60-day rolling")
            rolling_vol = (c["pf_daily"].rolling(60).std() * TRADING_DAYS**0.5).dropna()
            st.altair_chart(simple_line(rolling_vol), width="stretch")
            st.caption("How the portfolio's riskiness changed over time.")
        with col_rbeta:
            sec(f"Beta vs {BENCHMARK} · 60-day rolling")
            aligned = pd.concat({"pf": c["pf_daily"], "bench": c["bench_daily"]}, axis=1).dropna()
            rolling_beta = (
                aligned["pf"].rolling(60).cov(aligned["bench"])
                / aligned["bench"].rolling(60).var()
            ).dropna()
            st.altair_chart(
                simple_line(rolling_beta, color=PALETTE[0], y_format=".1f"),
                width="stretch",
            )
            st.caption("Above 1 you amplify the market, below 1 you dampen it.")

    col_contrib, col_alloc = st.columns([1.3, 1], gap="large")
    with col_contrib:
        sec("Who drove the result (in euros)")
        cum_by_ticker = per_ticker_cumulative_return(c["prices"])
        contributions_eur = pd.Series(
            {t: amounts[t] * float(cum_by_ticker.get(t, 0.0)) for t in amounts}
        )
        st.altair_chart(contribution_bars(contributions_eur), width="stretch")
        st.caption(
            "Invested amount × stock return (constant weights): "
            "the sum roughly reconstructs the total result."
        )
    with col_alloc:
        sec("Distribution")
        st.altair_chart(allocation_bars(amounts), width="stretch")

    sec("€100 in each stock")
    normalized = c["prices"] / c["prices"].iloc[0] * 100
    st.line_chart(normalized, color=PALETTE[: len(normalized.columns)], height=300)
