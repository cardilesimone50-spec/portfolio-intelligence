"""Vista Ottimizza: frontiera efficiente di Markowitz e pesi suggeriti."""

import pandas as pd
import streamlit as st

from src.portfolio.optimization import (
    efficient_frontier,
    max_sharpe_weights,
    minimum_variance_weights,
)
from src.portfolio.returns import portfolio_expected_return
from src.portfolio.risk import portfolio_volatility
from src.ui.components import sec
from src.views.common import TRADING_DAYS
from src.views.context import ViewContext
from src.visualization.charts import efficient_frontier_chart


def render(ctx: ViewContext) -> None:
    c = ctx.computed
    amounts, portfolio, risk_free = ctx.amounts, ctx.portfolio, ctx.risk_free

    if len(amounts) < 2:
        st.info("At least 2 stocks are needed for optimization.")
        return

    sec("Markowitz efficient frontier")
    st.caption(
        "For each level of risk, the best return achievable by combining "
        "your holdings (expected returns = historical arithmetic means, "
        "Markowitz convention)."
    )
    returns = c["returns"]
    candidates = {
        "Current": pd.Series({p["ticker"]: p["weight"] for p in portfolio}),
        "Minimum risk": minimum_variance_weights(returns),
        "Maximum Sharpe": max_sharpe_weights(returns, risk_free_rate=risk_free),
    }

    def pf_stats(weights: pd.Series) -> tuple[float, float]:
        pf = [{"ticker": t, "weight": float(w)} for t, w in weights.items() if w > 0]
        ret = portfolio_expected_return(returns, pf) * TRADING_DAYS
        vol = portfolio_volatility(returns, pf) * TRADING_DAYS**0.5
        return ret, vol

    points = pd.DataFrame(
        [
            {"nome": name, "annual_return": r, "annual_volatility": v}
            for name, (r, v) in ((n, pf_stats(w)) for n, w in candidates.items())
        ]
    )

    col_frontier, col_compare = st.columns([3, 2], gap="large")
    with col_frontier:
        st.altair_chart(
            efficient_frontier_chart(efficient_frontier(returns), points),
            width="stretch",
        )
    with col_compare:
        st.markdown("**Comparison**")
        compare = points.set_index("nome")
        compare["sharpe"] = (compare["annual_return"] - risk_free) / compare[
            "annual_volatility"
        ]
        st.dataframe(
            compare,
            column_config={
                "annual_return": st.column_config.NumberColumn("Return", format="percent"),
                "annual_volatility": st.column_config.NumberColumn(
                    "Volatility", format="percent"
                ),
                "sharpe": st.column_config.NumberColumn("Sharpe", format="%.2f"),
            },
        )
        st.markdown("**Suggested weights**")
        st.dataframe(
            pd.DataFrame(candidates),
            column_config={
                col: st.column_config.NumberColumn(col, format="percent") for col in candidates
            },
        )
