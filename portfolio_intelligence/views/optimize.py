"""Vista Ottimizza: frontiera efficiente di Markowitz e pesi suggeriti."""

import pandas as pd
import streamlit as st

from portfolio_intelligence.i18n import t
from portfolio_intelligence.portfolio import Portfolio
from portfolio_intelligence.portfolio.optimization import (
    efficient_frontier,
    max_sharpe_weights,
    minimum_variance_weights,
)
from portfolio_intelligence.portfolio.returns import portfolio_expected_return
from portfolio_intelligence.portfolio.risk import portfolio_volatility
from portfolio_intelligence.ui.components import sec, styled
from portfolio_intelligence.views.common import TRADING_DAYS
from portfolio_intelligence.views.context import ViewContext
from portfolio_intelligence.visualization.charts import efficient_frontier_chart
from portfolio_intelligence.visualization.charts import show as show_chart


def render(ctx: ViewContext) -> None:
    # garantito da app.py: questa vista è dispatchata solo con un portafoglio
    # calcolato (NEEDS_PORTFOLIO); l'assert documenta l'invariante e lascia
    # mypy restringere il tipo da qui in poi.
    assert ctx.computed is not None
    c = ctx.computed
    amounts, portfolio, risk_free = ctx.amounts, ctx.portfolio, ctx.risk_free

    if len(amounts) < 2:
        st.info(t("mvo.need_two"))
        return

    sec(t("mvo.title"))
    st.caption(t("mvo.caption"))
    returns = c["returns"]
    candidates = {
        t("mvo.current"): pd.Series({p["ticker"]: p["weight"] for p in portfolio}),
        t("mvo.min_var"): minimum_variance_weights(returns),
        t("mvo.max_sharpe"): max_sharpe_weights(returns, risk_free_rate=risk_free),
    }

    def pf_stats(weights: pd.Series) -> tuple[float, float]:
        pf: Portfolio = [{"ticker": t, "weight": float(w)} for t, w in weights.items() if w > 0]
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
        show_chart(
            efficient_frontier_chart(efficient_frontier(returns), points),
            width="stretch",
        )
    with col_compare:
        st.markdown(f"**{t('mvo.comparison')}**")
        compare = points.set_index("nome")
        compare["sharpe"] = (compare["annual_return"] - risk_free) / compare["annual_volatility"]
        st.dataframe(
            styled(
                compare,
                {
                    "annual_return": ("pct", 1, False),
                    "annual_volatility": ("pct", 1, False),
                    "sharpe": ("num", 2),
                },
            ),
            column_config={
                "_index": st.column_config.TextColumn(t("mvo.portfolio")),
                "annual_return": st.column_config.NumberColumn(t("mvo.exp_return")),
                "annual_volatility": st.column_config.NumberColumn(t("mvo.volatility")),
                "sharpe": st.column_config.NumberColumn("Sharpe"),
            },
        )
        st.markdown(f"**{t('mvo.weights')}**")
        st.caption(t("mvo.weights_caption"))
        weights_table = pd.DataFrame(candidates)
        st.dataframe(styled(weights_table, {col: ("pct", 1, False) for col in candidates}))
