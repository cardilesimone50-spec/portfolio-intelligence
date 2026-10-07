"""Vista Correlazioni: chi si muove insieme, heatmap del portafoglio."""

import pandas as pd
import streamlit as st

from portfolio_intelligence.analytics.interpret import interpret_correlation
from portfolio_intelligence.config import (
    CORRELATION_ELEVATED,
    CORRELATION_LOW,
    rolling_min_periods,
)
from portfolio_intelligence.i18n import t
from portfolio_intelligence.portfolio.returns import compute_daily_returns
from portfolio_intelligence.portfolio.risk import correlation_matrix, correlations_with
from portfolio_intelligence.ui.components import num, sec
from portfolio_intelligence.views.common import PERIOD_DAYS, market_db_required
from portfolio_intelligence.views.context import ViewContext
from portfolio_intelligence.visualization.charts import correlation_bars, correlation_heatmap
from portfolio_intelligence.visualization.charts import show as show_chart


def render(ctx: ViewContext) -> None:
    computed, amounts = ctx.computed, ctx.amounts

    sec(t("xc.title"))
    st.caption(t("xc.caption"))
    all_prices = market_db_required("corr")
    if all_prices is not None:
        col_sel, col_per = st.columns([2, 1])
        with col_sel:
            corr_ticker = st.selectbox(
                t("xc.reference"),
                sorted(all_prices.columns),
                index=None,
                placeholder=t("xc.reference_ph"),
            )
        with col_per:
            corr_period = st.selectbox(
                t("mkt.period"),
                list(PERIOD_DAYS),
                index=2,
                key="corr_period",
                format_func=lambda p: t(f"mkt.p_{PERIOD_DAYS[p]}"),
            )
        if corr_ticker:
            cutoff = all_prices.index[-1] - pd.Timedelta(days=PERIOD_DAYS[corr_period])
            window_returns = compute_daily_returns(all_prices.loc[all_prices.index >= cutoff])
            mp = rolling_min_periods(len(window_returns))
            corr = correlations_with(window_returns, corr_ticker, min_periods=mp)

            col_top, col_bottom = st.columns(2, gap="large")
            with col_top:
                st.markdown(t("xc.together", ticker=corr_ticker))
                show_chart(correlation_bars(corr.head(10)), width="stretch")
            with col_bottom:
                st.markdown(t("xc.opposite", ticker=corr_ticker))
                show_chart(correlation_bars(corr.tail(10).sort_values()), width="stretch")

    if computed is not None and len(amounts) >= 2:
        sec(t("xc.portfolio"))
        pf_corr = correlation_matrix(computed["returns"], min_periods=computed["min_periods"])
        avg_corr = computed["avg_corr"]
        pairs = pf_corr.where(
            pd.DataFrame(
                [[i < j for j in range(len(pf_corr))] for i in range(len(pf_corr))],
                index=pf_corr.index,
                columns=pf_corr.columns,
            )
        ).stack()

        col_metric, col_heat = st.columns([1, 2], gap="large")
        with col_metric:
            st.metric(t("xc.avg"), num(avg_corr))
            if avg_corr > CORRELATION_ELEVATED:
                st.warning(interpret_correlation(avg_corr))
            elif avg_corr > CORRELATION_LOW:
                st.info(interpret_correlation(avg_corr))
            else:
                st.success(interpret_correlation(avg_corr))
            if len(pairs):
                tightest = pairs.idxmax()
                st.caption(t("xc.tightest", a=tightest[0], b=tightest[1], value=num(pairs.max())))
        with col_heat:
            show_chart(correlation_heatmap(pf_corr), width="stretch")
