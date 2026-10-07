"""Vista Charts: analisi automatica, radar, galassia, mesi, simulatore what-if."""

import pandas as pd
import streamlit as st

from portfolio_intelligence.analytics.insights import generate_insights, monthly_returns
from portfolio_intelligence.analytics.simulation import simulate_shock
from portfolio_intelligence.i18n import t
from portfolio_intelligence.portfolio.returns import per_ticker_cumulative_return
from portfolio_intelligence.portfolio.risk import correlation_matrix
from portfolio_intelligence.ui.components import eur, pct, sec
from portfolio_intelligence.views.context import ViewContext
from portfolio_intelligence.visualization.charts import (
    galaxy_chart,
    monthly_bars,
    radar_chart,
    weight_vs_risk_bars,
)


def render(ctx: ViewContext) -> None:
    # garantito da app.py: questa vista è dispatchata solo con un portafoglio
    # calcolato (NEEDS_PORTFOLIO); l'assert documenta l'invariante e lascia
    # mypy restringere il tipo da qui in poi.
    assert ctx.computed is not None
    c = ctx.computed
    amounts, total, portfolio = ctx.amounts, ctx.total, ctx.portfolio
    period = ctx.period

    col_ai, col_radar = st.columns([1.3, 1], gap="large")
    with col_ai:
        sec(t("vis.auto"))
        insights = generate_insights(
            period,
            c["cum_return"],
            c["contributions"],
            c["avg_corr"],
            c["drawdown"],
            c["beta"],
            ctx.benchmark_label,
        )
        for insight in insights:
            st.markdown(insight)
        st.caption(t("vis.auto_caption"))
    with col_radar:
        sec(t("vis.radar"))
        st.altair_chart(radar_chart(c["radar"]), width="stretch")

    col_galaxy, col_timeline = st.columns([1.15, 1], gap="large")
    with col_galaxy:
        sec(t("vis.galaxy"))
        st.caption(t("vis.galaxy_caption"))
        if len(amounts) >= 2:
            corr = correlation_matrix(c["returns"], min_periods=c["min_periods"])
            weights_s = pd.Series({p["ticker"]: p["weight"] for p in portfolio})
            st.altair_chart(
                galaxy_chart(corr, weights_s, per_ticker_cumulative_return(c["prices"])),
                width="stretch",
            )
        else:
            st.info(t("vis.need_two"))
    with col_timeline:
        sec(t("vis.monthly"))
        monthly = monthly_returns(c["pf_daily"])
        if len(monthly) >= 2:
            st.altair_chart(monthly_bars(monthly), width="stretch")
            best, worst = monthly.idxmax(), monthly.idxmin()
            st.caption(
                t(
                    "vis.best_worst",
                    best=f"{best:%m/%Y}",
                    best_ret=pct(monthly.max(), signed=True),
                    worst=f"{worst:%m/%Y}",
                    worst_ret=pct(monthly.min(), signed=True),
                )
            )
        else:
            st.info(t("vis.too_short"))

    if len(amounts) >= 2:
        col_wr, col_wr_txt = st.columns([1.5, 1], gap="large")
        with col_wr:
            sec(t("vis.weight_risk"))
            weights_series_ui = pd.Series({p["ticker"]: p["weight"] for p in portfolio})
            st.altair_chart(
                weight_vs_risk_bars(weights_series_ui, c["contributions"]),
                width="stretch",
            )
        with col_wr_txt:
            sec(t("vis.how_to_read"))
            top_c = c["contributions"].index[0]
            gap = float(c["contributions"].iloc[0] - weights_series_ui.get(top_c, 0))
            st.markdown(
                t(
                    "vis.weight_risk_text",
                    ticker=top_c,
                    share=pct(c["contributions"].iloc[0], 0),
                    gap=pct(gap, 0, signed=True),
                )
            )
            st.caption(t("vis.mcr_caption"))

    sec(t("vis.shock"))
    col_sim_in, col_sim_out = st.columns([1, 2], gap="large")
    with col_sim_in:
        sim_ticker = st.selectbox(t("vis.shock_ticker"), sorted(amounts))
        shock_pct = st.slider(t("vis.shock_size"), -50, 50, -20, step=5, format="%d%%")
    with col_sim_out:
        impact = simulate_shock(c["returns"], portfolio, sim_ticker, shock_pct / 100)
        s1, s2, s3 = st.columns(3)
        s1.metric(t("vis.shock_today"), eur(total))
        s2.metric(
            t("vis.shock_total"),
            eur(total * (1 + impact["total"])),
            delta=pct(impact["total"], signed=True),
        )
        s3.metric(
            t("vis.shock_direct"),
            eur(total * (1 + impact["direct"])),
            delta=pct(impact["direct"], signed=True),
            delta_color="off",
        )
        st.caption(t("vis.shock_caption"))
