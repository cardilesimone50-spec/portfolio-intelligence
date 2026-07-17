"""Vista Correlazioni: chi si muove insieme, heatmap del portafoglio."""

import pandas as pd
import streamlit as st

from src.analytics.interpret import interpret_correlation
from src.portfolio.returns import compute_daily_returns
from src.portfolio.risk import correlation_matrix, correlations_with
from src.ui.components import sec
from src.views.common import PERIOD_DAYS, market_db_required
from src.views.context import ViewContext
from src.visualization.charts import correlation_bars, correlation_heatmap


def render(ctx: ViewContext) -> None:
    computed, amounts = ctx.computed, ctx.amounts

    sec("Which stocks move together")
    st.caption(
        "Correlation of daily returns: **+1** = identical, **0** = independent, **-1** = opposite."
    )
    all_prices = market_db_required("corr")
    if all_prices is None:
        st.info("The Nasdaq-100 database is required: run `python download_nasdaq100.py`.")
    else:
        col_sel, col_per = st.columns([2, 1])
        with col_sel:
            corr_ticker = st.selectbox(
                "Reference stock",
                sorted(all_prices.columns),
                index=None,
                placeholder="Choose a Nasdaq-100 stock...",
            )
        with col_per:
            corr_period = st.selectbox("Period", list(PERIOD_DAYS), index=2, key="corr_period")
        if corr_ticker:
            cutoff = all_prices.index[-1] - pd.Timedelta(days=PERIOD_DAYS[corr_period])
            window_returns = compute_daily_returns(all_prices.loc[all_prices.index >= cutoff])
            mp = max(15, min(60, len(window_returns) // 2))
            corr = correlations_with(window_returns, corr_ticker, min_periods=mp)

            col_top, col_bottom = st.columns(2, gap="large")
            with col_top:
                st.markdown(f"**Move TOGETHER with {corr_ticker}**")
                st.altair_chart(correlation_bars(corr.head(10)), width="stretch")
            with col_bottom:
                st.markdown(f"**INDEPENDENT or OPPOSITE to {corr_ticker}**")
                st.altair_chart(correlation_bars(corr.tail(10).sort_values()), width="stretch")

    if computed is not None and len(amounts) >= 2:
        sec("Your portfolio diversification")
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
            st.metric("Average correlation", f"{avg_corr:.2f}")
            if avg_corr > 0.6:
                st.warning(interpret_correlation(avg_corr))
            elif avg_corr > 0.3:
                st.info(interpret_correlation(avg_corr))
            else:
                st.success(interpret_correlation(avg_corr))
            if len(pairs):
                tightest = pairs.idxmax()
                st.caption(
                    f"Tightest pair: **{tightest[0]} – {tightest[1]}** ({pairs.max():+.2f})"
                )
        with col_heat:
            st.altair_chart(correlation_heatmap(pf_corr), width="stretch")
