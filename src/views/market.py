"""Vista Mercato: i costituenti Nasdaq-100 a confronto e ranking multifattore."""

import pandas as pd
import streamlit as st

from src.analytics.factors import composite_scores
from src.portfolio.returns import compute_daily_returns, per_ticker_cumulative_return
from src.ui.components import sec
from src.views.common import PERIOD_DAYS, TRADING_DAYS, market_db_required
from src.views.context import ViewContext
from src.visualization.charts import PALETTE


def render(ctx: ViewContext) -> None:
    sec("The 103 Nasdaq-100 constituents compared")
    all_prices = market_db_required("mercato")
    if all_prices is None:
        st.info("Database not downloaded yet: run `python download_nasdaq100.py`.")
        return

    ndx_period = st.selectbox("Comparison period", list(PERIOD_DAYS), index=2)
    cutoff = all_prices.index[-1] - pd.Timedelta(days=PERIOD_DAYS[ndx_period])
    window = all_prices.loc[all_prices.index >= cutoff]

    stats = (
        pd.DataFrame(
            {
                "period_return": per_ticker_cumulative_return(window),
                "annual_volatility": compute_daily_returns(window).std() * TRADING_DAYS**0.5,
            }
        )
        .rename_axis("ticker")
        .reset_index()
    )

    col_scatter, col_table = st.columns([3, 2], gap="large")
    with col_scatter:
        st.markdown(f"**Risk vs return ({ndx_period})** — each dot is a stock")
        st.scatter_chart(
            stats,
            x="annual_volatility",
            y="period_return",
            x_label="Annualized volatility",
            y_label=f"Cumulative return ({ndx_period})",
            color=PALETTE[0],
            height=420,
        )
    with col_table:
        st.markdown("**Full ranking**")
        st.dataframe(
            stats.sort_values("period_return", ascending=False),
            column_config={
                "ticker": st.column_config.TextColumn("Ticker"),
                "period_return": st.column_config.NumberColumn(
                    f"Return ({ndx_period})", format="percent"
                ),
                "annual_volatility": st.column_config.NumberColumn(
                    "Annual volatility", format="percent"
                ),
            },
            hide_index=True,
            height=420,
        )
    st.caption(
        "Cumulative return over the period (USD prices). "
        "Refresh the data with `python download_nasdaq100.py`."
    )

    sec("PI Score — multifactor ranking")
    st.caption(
        "Composite score 0-100: **50% 12-1 month momentum** (Jegadeesh & "
        "Titman 1993), **30% low volatility** (Baker et al. 2011), "
        "**20% trend** (distance from the 200-day average). Historical "
        "regularities documented in the literature, not guarantees — and "
        "not investment advice."
    )
    pi_window = compute_daily_returns(all_prices).tail(TRADING_DAYS)
    pi_ranking = composite_scores(pi_window).dropna().head(15)
    st.dataframe(
        pi_ranking.rename_axis("ticker").reset_index(),
        column_config={
            "ticker": st.column_config.TextColumn("Ticker"),
            "momentum": st.column_config.ProgressColumn(
                "Momentum", min_value=0, max_value=100, format="%.0f"
            ),
            "low_vol": st.column_config.ProgressColumn(
                "Low volatility", min_value=0, max_value=100, format="%.0f"
            ),
            "trend": st.column_config.ProgressColumn(
                "Trend", min_value=0, max_value=100, format="%.0f"
            ),
            "pi_score": st.column_config.NumberColumn("PI Score", format="%.0f"),
        },
        hide_index=True,
        width="stretch",
    )
