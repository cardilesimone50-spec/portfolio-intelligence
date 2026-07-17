"""Vista Clienti: il book dell'advisor con semaforo, valore e problema principale."""

import streamlit as st

from src.analytics.insights import (
    dna_scores,
    find_problems,
    health_breakdown,
    portfolio_health_score,
    radar_scores,
    risk_contributions,
    usd_exposure,
)
from src.analytics.performance import max_drawdown
from src.data.fx import convert_to_eur
from src.data.store import list_portfolios
from src.portfolio.returns import compute_daily_returns, portfolio_daily_returns
from src.portfolio.risk import average_pairwise_correlation, portfolio_volatility
from src.ui.components import empty_state, eur, sec
from src.ui.theme import AMBER
from src.views.common import (
    TRADING_DAYS,
    cached_eurusd,
    cached_fundamentals,
    cached_prices,
)
from src.views.context import ViewContext
from src.visualization.charts import GAIN, LOSS


@st.cache_data(ttl=900, show_spinner=False)
def quick_client_analysis(items: tuple, period_key: str, eur_flag: bool) -> dict:
    amounts_c = dict(items)
    total_c = sum(amounts_c.values())
    pf_c = [{"ticker": t, "weight": a / total_c} for t, a in amounts_c.items()]
    prices_c = cached_prices(tuple(sorted(amounts_c)), period_key)
    if eur_flag:
        prices_c = convert_to_eur(prices_c, cached_eurusd(period_key))
    returns_c = compute_daily_returns(prices_c)
    daily_c = portfolio_daily_returns(returns_c, pf_c)
    value_c = (1 + daily_c).cumprod()
    vol_c = portfolio_volatility(returns_c, pf_c) * TRADING_DAYS**0.5
    dd_c = max_drawdown(value_c)
    mp_c = max(15, min(60, len(returns_c) // 2))
    corr_c = average_pairwise_correlation(returns_c, min_periods=mp_c)
    radar_c = radar_scores(vol_c, pf_c, dd_c, corr_c)
    fund_c = cached_fundamentals(tuple(sorted(amounts_c)))
    dna_c = dna_scores(fund_c, pf_c, vol_c, corr_c)
    breakdown_c = health_breakdown(dna_c, radar_c, usd_exposure(pf_c))
    contributions_c = risk_contributions(returns_c, pf_c)
    problems_c = find_problems(pf_c, fund_c, contributions_c, corr_c, radar_c)
    return {
        "health": portfolio_health_score(breakdown_c),
        "value": total_c * float(value_c.iloc[-1]),
        "invested": total_c,
        "cum": float(value_c.iloc[-1] - 1),
        "vol": vol_c,
        "problem": problems_c[0].replace("**", "")
        if problems_c
        else "No problems flagged by the monitored rules.",
    }


def render(ctx: ViewContext) -> None:
    advisor, period, in_eur = ctx.advisor, ctx.period, ctx.in_eur

    sec("Advisor view — all saved portfolios")
    st.caption(
        "Each saved portfolio is a client: status light, value, Health Score "
        "and the most urgent problem at a glance. To open one: "
        "sidebar → Saved portfolios → Load."
    )

    book = list_portfolios(advisor)
    if not book:
        empty_state(
            "No clients in the book",
            "Save at least one portfolio (sidebar → Saved portfolios) "
            "to see it appear here with status light and main problem.",
            icon="folder",
        )
        return

    rows_html = ""
    failures = []
    with st.spinner("Analyzing the client book..."):
        for client_name in sorted(book):
            try:
                a = quick_client_analysis(
                    tuple(sorted(book[client_name].items())), period, in_eur
                )
            except ValueError as exc:
                failures.append(f"{client_name}: {exc}")
                continue
            color = GAIN if a["health"] >= 67 else AMBER if a["health"] >= 34 else LOSS
            chg_css = "up" if a["cum"] >= 0 else "down"
            rows_html += f"""
            <div class="kpi" style="display:flex;align-items:center;
                 gap:16px;margin-bottom:10px;min-width:100%">
              <div style="width:10px;height:10px;border-radius:50%;
                   background:{color};flex-shrink:0"></div>
              <div style="min-width:150px">
                <div style="font-weight:700">{client_name}</div>
                <div class="kpi-sub">{eur(a["invested"])} invested ·
                     vol. {a["vol"]:.0%}</div>
              </div>
              <div style="min-width:120px">
                <div class="kpi-sub">VALUE</div>
                <div style="font-weight:700;font-variant-numeric:tabular-nums">
                     {eur(a["value"])}
                     <span class="chg {chg_css}" style="font-size:.8rem">
                     {a["cum"]:+.1%}</span></div>
              </div>
              <div style="flex:1" class="kpi-sub">{a["problem"]}</div>
              <div style="font-family:var(--font-display);font-size:1.5rem;
                   font-weight:700;color:{color}">{a["health"]}
                   <span style="font-size:.7rem;color:var(--muted)">/100</span>
              </div>
            </div>"""
    st.markdown(rows_html, unsafe_allow_html=True)
    for failure in failures:
        st.warning(f"Analysis failed — {failure}")
    st.caption(
        f"{len(book)} clients · horizon {period} · "
        + ("EUR values, currency included" if in_eur else "original currencies")
        + " · analyses refreshed every 15 minutes."
    )
