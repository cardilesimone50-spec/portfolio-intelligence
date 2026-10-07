"""Vista Analisi (metriche): rendimento, rischio, benchmark, rolling, contributi."""

import pandas as pd
import streamlit as st

from portfolio_intelligence.analytics.interpret import (
    interpret_beta,
    interpret_drawdown,
    interpret_sharpe,
    interpret_sortino,
    interpret_volatility,
)
from portfolio_intelligence.analytics.performance import (
    annualized_sharpe,
    rolling_beta,
    sortino_ratio,
)
from portfolio_intelligence.data.fx import is_usd_listing
from portfolio_intelligence.i18n import t
from portfolio_intelligence.portfolio.returns import (
    compute_daily_returns,
    per_ticker_cumulative_return,
)
from portfolio_intelligence.ui.components import eur, num, pct, sec
from portfolio_intelligence.views.common import TRADING_DAYS, load_market_db
from portfolio_intelligence.views.context import ViewContext
from portfolio_intelligence.visualization.charts import (
    PALETTE,
    allocation_bars,
    benchmark_overlay,
    contribution_bars,
    multi_line,
    returns_histogram,
    simple_line,
    underwater_chart,
)
from portfolio_intelligence.visualization.charts import show as show_chart


def render(ctx: ViewContext) -> None:
    # garantito da app.py: questa vista è dispatchata solo con un portafoglio
    # calcolato (NEEDS_PORTFOLIO); l'assert documenta l'invariante e lascia
    # mypy restringere il tipo da qui in poi.
    assert ctx.computed is not None
    c = ctx.computed
    amounts, total, portfolio = ctx.amounts, ctx.total, ctx.portfolio
    risk_free, in_eur = ctx.risk_free, ctx.in_eur
    benchmark = ctx.benchmark_label

    sharpe = annualized_sharpe(c["returns"], portfolio, risk_free_rate=risk_free)
    sortino = sortino_ratio(c["returns"], portfolio, risk_free_rate=risk_free)

    # percentile di volatilità contro i singoli titoli del Nasdaq-100 (se in DB)
    _db = load_market_db()
    universe_vols = (
        compute_daily_returns(_db).std() * TRADING_DAYS**0.5 if _db is not None else None
    )

    sec(t("an.return"))
    m1, m2, m3, m4 = st.columns(4)
    m1.metric(t("an.market_value"), eur(total))
    m2.metric(
        t("an.cagr"),
        eur(total * c["annual_ret"]),
        delta=pct(c["annual_ret"], signed=True),
        help=t("an.cagr_help"),
    )
    m3.metric(t("an.sharpe"), num(sharpe), help=t("an.sharpe_help", rf=pct(risk_free)))
    m3.caption(interpret_sharpe(sharpe))
    m4.metric(t("an.sortino"), num(sortino))
    m4.caption(interpret_sortino(sortino, sharpe))

    sec(t("an.risk"))
    r1, r2, r3, r4 = st.columns(4)
    r1.metric(
        t("an.vol"),
        pct(c["annual_vol"]),
        delta=f"± {eur(total * c['annual_vol'])}",
        delta_color="off",
    )
    r1.caption(interpret_volatility(c["annual_vol"], universe_vols))
    r2.metric(
        t("an.maxdd"), pct(c["drawdown"]), delta=eur(total * c["drawdown"]), delta_color="off"
    )
    r2.caption(interpret_drawdown(c["drawdown"]))
    r3.metric(t("an.var"), pct(c["var_95"]), delta=eur(total * c["var_95"]), delta_color="off")
    r3.caption(t("an.var_caption"))
    r4.metric(
        t("an.beta", benchmark=benchmark),
        num(c["beta"]),
        delta=t("an.alpha_delta", alpha=pct(c["alpha"], signed=True)),
        delta_color="off",
    )
    r4.caption(interpret_beta(c["beta"], benchmark))
    st.caption(t("an.estimates"))

    sec(t("an.vs_bench", benchmark=benchmark))
    bench_value = (1 + c["bench_daily"]).cumprod()
    show_chart(
        benchmark_overlay(c["pf_value"], bench_value, benchmark),
        width="stretch",
    )
    excess = c["cum_return"] - float(bench_value.iloc[-1] - 1)
    # l'effetto cambio c'è solo se portafoglio o benchmark quotano in dollari
    fx_effect = in_eur and (c["usd_weight"] > 0 or is_usd_listing(ctx.benchmark))
    st.caption(
        t("an.excess", excess=pct(excess, signed=True)) + (t("an.excess_fx") if fx_effect else ".")
    )
    if ctx.benchmark_price_index:
        st.caption(t("bench.price_index_note", benchmark=benchmark))

    col_dd, col_hist = st.columns(2, gap="large")
    with col_dd:
        sec(t("an.underwater"))
        show_chart(underwater_chart(c["pf_value"]), width="stretch")
        st.caption(t("an.underwater_caption"))
    with col_hist:
        sec(t("an.distribution"))
        show_chart(returns_histogram(c["pf_daily"], c["var_95"]), width="stretch")
        st.caption(t("an.distribution_caption"))

    if len(c["pf_daily"]) >= 80:
        col_rvol, col_rbeta = st.columns(2, gap="large")
        with col_rvol:
            sec(t("an.rolling_vol"))
            rolling_vol = (c["pf_daily"].rolling(60).std() * TRADING_DAYS**0.5).dropna()
            show_chart(simple_line(rolling_vol), width="stretch")
            st.caption(t("an.rolling_vol_caption"))
        with col_rbeta:
            sec(t("an.rolling_beta", benchmark=benchmark))
            beta_60d = rolling_beta(c["pf_daily"], c["bench_daily"], window=60)
            show_chart(
                simple_line(beta_60d, color=PALETTE[0], y_format=".1f"),
                width="stretch",
            )
            st.caption(t("an.rolling_beta_caption"))

    col_contrib, col_alloc = st.columns([1.3, 1], gap="large")
    with col_contrib:
        sec(t("an.attribution"))
        cum_by_ticker = per_ticker_cumulative_return(c["prices"])
        contributions_eur = pd.Series(
            {t: amounts[t] * float(cum_by_ticker.get(t, 0.0)) for t in amounts}
        )
        show_chart(contribution_bars(contributions_eur), width="stretch")
        st.caption(t("an.attribution_caption"))
    with col_alloc:
        sec(t("an.allocation"))
        show_chart(allocation_bars(amounts), width="stretch")

    sec(t("an.base100"))
    normalized = c["prices"] / c["prices"].iloc[0] * 100
    show_chart(multi_line(normalized, height=300), width="stretch")
