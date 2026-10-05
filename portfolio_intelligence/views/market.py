"""Vista Mercato: i costituenti Nasdaq-100 a confronto e ranking multifattore."""

import pandas as pd
import streamlit as st

from portfolio_intelligence.analytics.factors import composite_scores
from portfolio_intelligence.i18n import t
from portfolio_intelligence.portfolio.returns import (
    compute_daily_returns,
    per_ticker_cumulative_return,
)
from portfolio_intelligence.ui.components import sec
from portfolio_intelligence.views.common import PERIOD_DAYS, TRADING_DAYS, market_db_required
from portfolio_intelligence.views.context import ViewContext
from portfolio_intelligence.visualization.charts import PALETTE


def render(ctx: ViewContext) -> None:
    sec(t("mkt.title"))
    all_prices = market_db_required("mercato")
    if all_prices is None:
        st.info(t("mkt.no_db"))
        return

    ndx_period = st.selectbox(
        t("mkt.period"),
        list(PERIOD_DAYS),
        index=2,
        format_func=lambda p: t(f"mkt.p_{PERIOD_DAYS[p]}"),
    )
    period_label = t(f"mkt.p_{PERIOD_DAYS[ndx_period]}")
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
        st.markdown(t("mkt.scatter", period=period_label))
        st.scatter_chart(
            stats,
            x="annual_volatility",
            y="period_return",
            x_label=t("mkt.vol"),
            y_label=t("mkt.ret", period=period_label),
            color=PALETTE[0],
            height=420,
        )
    with col_table:
        st.markdown(f"**{t('mkt.ranking')}**")
        st.dataframe(
            stats.sort_values("period_return", ascending=False),
            column_config={
                "ticker": st.column_config.TextColumn("Ticker"),
                "period_return": st.column_config.NumberColumn(
                    t("mkt.ret", period=period_label), format="percent"
                ),
                "annual_volatility": st.column_config.NumberColumn(t("mkt.vol"), format="percent"),
            },
            hide_index=True,
            height=420,
        )
    st.caption(t("mkt.caption"))

    sec(t("mkt.pi_title"))
    st.caption(t("mkt.pi_caption"))
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
                t("mkt.low_vol"), min_value=0, max_value=100, format="%.0f"
            ),
            "trend": st.column_config.ProgressColumn(
                "Trend", min_value=0, max_value=100, format="%.0f"
            ),
            "pi_score": st.column_config.NumberColumn("PI Score", format="%.0f"),
        },
        hide_index=True,
        width="stretch",
    )
