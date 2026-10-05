"""Vista Backtest: strategie a confronto senza look-ahead, costi inclusi."""

import pandas as pd
import streamlit as st

from portfolio_intelligence.analytics.backtest import (
    buy_and_hold,
    equal_weight,
    max_sharpe,
    min_variance,
    momentum_top,
    run_backtest,
)
from portfolio_intelligence.analytics.factors import multifactor_weights
from portfolio_intelligence.i18n import t
from portfolio_intelligence.ui.components import pct, sec
from portfolio_intelligence.views.common import TRADING_DAYS, cached_prices, market_db_required
from portfolio_intelligence.views.context import ViewContext
from portfolio_intelligence.visualization.charts import multi_line

# orizzonte → giorni e periodo Yahoo
HORIZON_DAYS = {"1y": 365, "2y": 730, "5y": 1826}

# strategie: id stabile → chiave di traduzione (le etichette cambiano con la lingua)
MARKET_STRATEGIES = ("equal", "momentum", "multifactor")
CLIENT_STRATEGIES = ("buy_hold", "max_sharpe", "min_var")


def render(ctx: ViewContext) -> None:
    amounts = ctx.amounts

    sec(t("bt.title"))
    st.caption(t("bt.caption"))
    all_prices = market_db_required("backtest")
    if all_prices is None:
        st.info(t("xc.no_db"))
        return

    options = list(MARKET_STRATEGIES)
    if len(amounts) >= 2:
        options += CLIENT_STRATEGIES
    chosen = st.multiselect(
        t("bt.strategies"),
        options,
        default=options[:3],
        format_func=lambda s: t(f"bt.s_{s}"),
    )
    col_bt1, col_bt2 = st.columns(2)
    with col_bt1:
        bt_years = st.select_slider(
            t("bt.horizon"), list(HORIZON_DAYS), "5y", format_func=lambda h: t(f"bt.h_{h}")
        )
    with col_bt2:
        cost_bps = st.slider(t("bt.costs"), 0, 50, 20, step=5, help=t("bt.costs_help"))
    cutoff = all_prices.index[-1] - pd.Timedelta(days=HORIZON_DAYS[bt_years])
    window = all_prices.loc[all_prices.index >= cutoff]

    if not chosen:
        return

    with st.spinner(t("bt.running")):
        curves = {}
        try:
            if "equal" in chosen:
                curves["equal"] = run_backtest(window, equal_weight, cost_bps=cost_bps)
            if "momentum" in chosen:
                curves["momentum"] = run_backtest(
                    window,
                    lambda w: momentum_top(w, top_n=10),
                    cost_bps=cost_bps,
                )
            if "multifactor" in chosen:
                curves["multifactor"] = run_backtest(
                    window,
                    lambda w: multifactor_weights(w, top_n=10),
                    lookback=273,  # serve ~1 anno per il momentum 12-1
                    cost_bps=cost_bps,
                )
            if len(amounts) >= 2:
                my_tickers = [t for t in sorted(amounts) if t in window.columns]
                my_prices = (
                    window[my_tickers]
                    if len(my_tickers) == len(amounts)
                    else cached_prices(tuple(sorted(amounts)), bt_years)
                )
                weights_now = pd.Series(amounts) / sum(amounts.values())
                if "buy_hold" in chosen:
                    curves["buy_hold"] = buy_and_hold(my_prices, weights_now)
                if "max_sharpe" in chosen:
                    curves["max_sharpe"] = run_backtest(my_prices, max_sharpe, cost_bps=cost_bps)
                if "min_var" in chosen:
                    curves["min_var"] = run_backtest(my_prices, min_variance, cost_bps=cost_bps)
        except ValueError as exc:
            st.error(f"{exc}")

    if curves:
        curves = {t(f"bt.s_{key}"): curve for key, curve in curves.items()}
        equity = pd.DataFrame(curves).dropna(how="all")
        cols = st.columns(len(curves))
        for col, (name, curve) in zip(cols, curves.items(), strict=False):
            col.metric(name, pct(curve.iloc[-1] / 100 - 1, 0, signed=True))
        st.altair_chart(multi_line(equity, height=380), width="stretch")

        strategy_stats = pd.DataFrame(
            [
                {
                    "strategy": name,
                    "return": curve.iloc[-1] / 100 - 1,
                    "volatility": curve.pct_change().std() * TRADING_DAYS**0.5,
                    "drawdown": float((curve / curve.cummax() - 1).min()),
                }
                for name, curve in curves.items()
            ]
        )
        st.dataframe(
            strategy_stats,
            column_config={
                "strategy": st.column_config.TextColumn(t("bt.col_strategy")),
                "return": st.column_config.NumberColumn(t("bt.col_return"), format="percent"),
                "volatility": st.column_config.NumberColumn(t("mkt.vol"), format="percent"),
                "drawdown": st.column_config.NumberColumn(t("m.maxdd"), format="percent"),
            },
            hide_index=True,
            width="stretch",
        )
        st.caption(t("bt.footer", bps=cost_bps))
