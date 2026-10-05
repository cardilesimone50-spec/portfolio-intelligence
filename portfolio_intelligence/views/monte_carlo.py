"""Vista "Simulazione scenari (Monte Carlo)" della scheda cliente Advisor.

Solo area Advisor: l'area Investor dichiara di non fare previsioni di
rendimento, quindi questa proiezione non vi compare (né nel suo PDF).
"""

import pandas as pd
import streamlit as st

from portfolio_intelligence.analytics.monte_carlo import (
    METHODS,
    MonteCarloResult,
    scenario_table,
    simulate,
)
from portfolio_intelligence.config import TRADING_DAYS
from portfolio_intelligence.i18n import t
from portfolio_intelligence.ui.components import eur, notice, sec
from portfolio_intelligence.views.context import ViewContext
from portfolio_intelligence.visualization.monte_carlo_charts import fan_chart

HORIZONS = [1, 3, 5]
SIMULATIONS = [500, 1000, 2000, 5000]
SHORT_HISTORY_DAYS = 2 * TRADING_DAYS


@st.cache_data(ttl=3600, show_spinner=False, max_entries=64)
def cached_simulation(
    returns: pd.DataFrame,
    weights: tuple[tuple[str, float], ...],
    initial_value: float,
    horizon_years: int,
    n_simulations: int,
    method: str,
) -> MonteCarloResult:
    return simulate(
        initial_value,
        dict(weights),
        returns,
        horizon_years=horizon_years,
        n_simulations=n_simulations,
        method=method,
        random_state=42,
    )


def _inputs(ctx: ViewContext) -> tuple[pd.DataFrame, tuple[tuple[str, float], ...]]:
    assert ctx.computed is not None
    weights = tuple(sorted((p["ticker"], float(p["weight"])) for p in ctx.portfolio))
    returns = ctx.computed["returns"][[ticker for ticker, _ in weights]]
    return returns, weights


def report_projection(ctx: ViewContext) -> dict | None:
    """Proiezione per il PDF: bootstrap, 1000 simulazioni, 5 anni.

    Restituisce scenari p10/p50/p90 a 1, 3 e 5 anni ("rows"), i percentili mese
    per mese per il ventaglio ("paths"), i tassi annui impliciti, la quota di
    simulazioni in perdita e i parametri del metodo, da dichiarare nel report.
    """
    if ctx.computed is None or not ctx.portfolio or ctx.total <= 0:
        return None
    returns, weights = _inputs(ctx)
    try:
        result = cached_simulation(returns, weights, float(ctx.total), 5, 1000, "bootstrap")
    except ValueError:
        return None
    return {
        "rows": scenario_table(result),
        "paths": result.paths,
        "cagr": {f"p{p}": result.cagr(p) for p in (10, 50, 90)},
        "prob_loss": result.prob_loss,
        "method": result.method,
        "n": result.n_simulations,
        "horizon": result.horizon_years,
    }


def _kpi(label: str, value: str, sub: str) -> str:
    return (
        f'<div class="kpi"><div class="kpi-label">{label}</div>'
        f'<div class="kpi-value">{value}</div><div class="kpi-sub">{sub}</div></div>'
    )


def render(ctx: ViewContext) -> None:
    assert ctx.computed is not None
    sec(t("mc.title"))
    st.caption(t("mc.intro"))

    h_col, m_col, n_col = st.columns([1, 1.3, 1])
    horizon = h_col.select_slider(
        t("mc.horizon"), HORIZONS, value=3, format_func=lambda y: t("mc.years", n=y)
    )
    method = m_col.segmented_control(
        t("mc.method"),
        list(METHODS),
        default="bootstrap",
        format_func=lambda m: t(f"mc.method_{m}"),
    )
    n_sims = n_col.select_slider(t("mc.simulations"), SIMULATIONS, value=1000)

    returns, weights = _inputs(ctx)
    history = returns.dropna()
    try:
        result = cached_simulation(
            returns, weights, float(ctx.total), int(horizon), int(n_sims), method or "bootstrap"
        )
    except ValueError as exc:
        st.warning(t("mc.unavailable", err=exc))
        return

    p50, p10 = result.final(50), result.final(10)
    st.markdown(
        '<div class="kpi-row">'
        + _kpi(
            t("mc.kpi_median", years=horizon),
            eur(p50),
            t(
                "mc.kpi_vs_today",
                pct=f"{p50 / result.initial_value - 1:+.1%}",
                cagr=f"{result.cagr(50):+.1%}",
            ),
        )
        + _kpi(
            t("mc.kpi_prudent"),
            eur(p10),
            t(
                "mc.kpi_vs_today",
                pct=f"{p10 / result.initial_value - 1:+.1%}",
                cagr=f"{result.cagr(10):+.1%}",
            ),
        )
        + _kpi(
            t("mc.kpi_positive"),
            f"{result.prob_gain:.0%}",
            t("mc.kpi_positive_sub", p5=eur(result.final(5))),
        )
        + "</div>",
        unsafe_allow_html=True,
    )

    st.altair_chart(fan_chart(result), width="stretch")
    st.caption(
        t(
            "mc.history",
            n=len(history),
            start=f"{history.index[0]:%d/%m/%Y}",
            end=f"{history.index[-1]:%d/%m/%Y}",
            sims=f"{result.n_simulations:,}".replace(",", "."),
        )
    )
    if len(history) < SHORT_HISTORY_DAYS:
        st.warning(t("mc.short_history"))
    notice(t("mc.disclaimer"))
    with st.expander(t("mc.method_title")):
        st.markdown(t("mc.method_text"))
