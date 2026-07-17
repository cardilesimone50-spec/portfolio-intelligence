"""Vista Backtest: strategie a confronto senza look-ahead, costi inclusi."""

import pandas as pd
import streamlit as st

from src.analytics.backtest import (
    buy_and_hold,
    equal_weight,
    max_sharpe,
    min_variance,
    momentum_top,
    run_backtest,
)
from src.analytics.factors import multifactor_weights
from src.ui.components import sec
from src.views.common import TRADING_DAYS, cached_prices, market_db_required
from src.views.context import ViewContext
from src.visualization.charts import PALETTE

# etichette dello slider orizzonte → giorni e periodo Yahoo
HORIZON_DAYS = {"1 year": 365, "2 years": 730, "5 years": 1826}
HORIZON_PERIOD = {"1 year": "1y", "2 years": "2y", "5 years": "5y"}


def render(ctx: ViewContext) -> None:
    amounts = ctx.amounts

    sec("What if you had followed a strategy?")
    st.caption(
        "Quarterly rebalancing, weights computed only on prior data "
        "(no look-ahead). Limits: no transaction costs, USD prices, "
        "universe = CURRENT Nasdaq-100 constituents (survivorship bias)."
    )
    all_prices = market_db_required("backtest")
    if all_prices is None:
        st.info("The Nasdaq-100 database is required: run `python download_nasdaq100.py`.")
        return

    options = [
        "Equal-weight Nasdaq-100",
        "Momentum (top 10 at 6 months)",
        "PI Multifactor (top 10)",
    ]
    if len(amounts) >= 2:
        options += [
            "Your portfolio (buy & hold)",
            "Maximum Sharpe on your holdings",
            "Minimum variance on your holdings",
        ]
    chosen = st.multiselect("Strategies to compare", options, default=options[:3])
    col_bt1, col_bt2 = st.columns(2)
    with col_bt1:
        bt_years = st.select_slider("Horizon", ["1 year", "2 years", "5 years"], "5 years")
    with col_bt2:
        cost_bps = st.slider(
            "Transaction costs (bps per rebalance)",
            0,
            50,
            20,
            step=5,
            help="20 bps = 0.20% of traded value: realistic for retail on liquid "
            "stocks. Buy & hold pays only the initial purchase.",
        )
    cutoff = all_prices.index[-1] - pd.Timedelta(days=HORIZON_DAYS[bt_years])
    window = all_prices.loc[all_prices.index >= cutoff]

    if not chosen:
        return

    with st.spinner("Running the backtests..."):
        curves = {}
        try:
            if "Equal-weight Nasdaq-100" in chosen:
                curves["Equal-weight Nasdaq-100"] = run_backtest(
                    window, equal_weight, cost_bps=cost_bps
                )
            if "Momentum (top 10 at 6 months)" in chosen:
                curves["Momentum (top 10 at 6 months)"] = run_backtest(
                    window,
                    lambda w: momentum_top(w, top_n=10),
                    cost_bps=cost_bps,
                )
            if "PI Multifactor (top 10)" in chosen:
                curves["PI Multifactor (top 10)"] = run_backtest(
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
                    else cached_prices(tuple(sorted(amounts)), HORIZON_PERIOD[bt_years])
                )
                weights_now = pd.Series(amounts) / sum(amounts.values())
                if "Your portfolio (buy & hold)" in chosen:
                    curves["Your portfolio (buy & hold)"] = buy_and_hold(
                        my_prices, weights_now
                    )
                if "Maximum Sharpe on your holdings" in chosen:
                    curves["Maximum Sharpe on your holdings"] = run_backtest(
                        my_prices, max_sharpe, cost_bps=cost_bps
                    )
                if "Minimum variance on your holdings" in chosen:
                    curves["Minimum variance on your holdings"] = run_backtest(
                        my_prices, min_variance, cost_bps=cost_bps
                    )
        except ValueError as exc:
            st.error(f"{exc}")

    if curves:
        equity = pd.DataFrame(curves).dropna(how="all")
        cols = st.columns(len(curves))
        for col, (name, curve) in zip(cols, curves.items(), strict=False):
            col.metric(name, f"{curve.iloc[-1] / 100 - 1:+.0%}")
        st.line_chart(equity, color=PALETTE[: len(curves)], height=380)

        strategy_stats = pd.DataFrame(
            [
                {
                    "Strategy": name,
                    "Return": curve.iloc[-1] / 100 - 1,
                    "Annual volatility": curve.pct_change().std() * TRADING_DAYS**0.5,
                    "Max drawdown": float((curve / curve.cummax() - 1).min()),
                }
                for name, curve in curves.items()
            ]
        )
        st.dataframe(
            strategy_stats,
            column_config={
                "Return": st.column_config.NumberColumn(format="percent"),
                "Annual volatility": st.column_config.NumberColumn(format="percent"),
                "Max drawdown": st.column_config.NumberColumn(format="percent"),
            },
            hide_index=True,
            width="stretch",
        )
        st.caption(
            f"Base-100 curves, {cost_bps} bps cost per rebalance. "
            "Return isn't everything: look at volatility and drawdown."
        )
