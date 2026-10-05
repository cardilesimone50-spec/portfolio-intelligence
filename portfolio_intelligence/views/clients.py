"""Analisi rapida di un portafoglio cliente, per il book dell'area Advisor."""

import streamlit as st

from portfolio_intelligence.analytics.insights import (
    dna_scores,
    find_problems,
    health_breakdown,
    portfolio_health_score,
    radar_scores,
    risk_contributions,
    usd_exposure,
)
from portfolio_intelligence.analytics.performance import max_drawdown
from portfolio_intelligence.config import HEALTH_SCORE_FAIR, HEALTH_SCORE_GOOD, rolling_min_periods
from portfolio_intelligence.data.fx import convert_to_eur
from portfolio_intelligence.i18n import t
from portfolio_intelligence.portfolio import Portfolio
from portfolio_intelligence.portfolio.positions import normalize_portfolio, position_table, totals
from portfolio_intelligence.portfolio.returns import compute_daily_returns, portfolio_daily_returns
from portfolio_intelligence.portfolio.risk import (
    average_pairwise_correlation,
    portfolio_volatility,
)
from portfolio_intelligence.ui.theme import AMBER
from portfolio_intelligence.views.common import (
    TRADING_DAYS,
    analysis_fundamentals,
    cached_eurusd,
    cached_prices,
)
from portfolio_intelligence.visualization.charts import GAIN, LOSS


@st.cache_data(ttl=900, show_spinner=False)
def quick_client_analysis(items: tuple, period_key: str, eur_flag: bool, lang: str = "en") -> dict:
    """Health, valore, rischio e problema principale di un cliente.

    `lang` entra nella chiave di cache: il testo del problema è tradotto.
    """
    positions_c = normalize_portfolio(dict(items))
    prices_native = cached_prices(tuple(sorted(positions_c)), period_key)
    if eur_flag:
        prices_c = convert_to_eur(prices_native, cached_eurusd(period_key))
    else:
        prices_c = prices_native
    last_native = prices_native.ffill().iloc[-1]
    fx_factor = (prices_c.ffill().iloc[-1] / last_native).fillna(1.0)
    table_c = position_table(positions_c, last_native, fx_factor)
    agg_c = totals(table_c)
    amounts_c = {ticker: float(v) for ticker, v in table_c["value"].items() if v == v and v > 0}
    total_c = sum(amounts_c.values())
    pf_c: Portfolio = [{"ticker": t, "weight": a / total_c} for t, a in amounts_c.items()]
    returns_c = compute_daily_returns(prices_c)
    daily_c = portfolio_daily_returns(returns_c, pf_c)
    value_c = (1 + daily_c).cumprod()
    vol_c = portfolio_volatility(returns_c, pf_c) * TRADING_DAYS**0.5
    dd_c = max_drawdown(value_c)
    mp_c = rolling_min_periods(len(returns_c))
    corr_c = average_pairwise_correlation(returns_c, min_periods=mp_c)
    radar_c = radar_scores(vol_c, pf_c, dd_c, corr_c)
    fund_c = analysis_fundamentals(tuple(sorted(amounts_c)))
    dna_c = dna_scores(fund_c, pf_c, vol_c, corr_c)
    breakdown_c = health_breakdown(dna_c, radar_c, usd_exposure(pf_c))
    contributions_c = risk_contributions(returns_c, pf_c)
    problems_c = find_problems(pf_c, fund_c, contributions_c, corr_c, radar_c)
    return {
        "health": portfolio_health_score(breakdown_c),
        "value": total_c,  # valore attuale reale: quantità × ultimo prezzo
        "invested": agg_c["cost"],
        "cum": float(value_c.iloc[-1] - 1),
        "pnl_pct": agg_c["pnl_pct"],
        "vol": vol_c,
        "problem": problems_c[0].replace("**", "") if problems_c else t("chk.no_problems"),
    }


def status_color(health: float) -> str:
    """Colore di stato dell'Health Score (verde, ambra, rosso)."""
    if health >= HEALTH_SCORE_GOOD:
        return GAIN
    return AMBER if health >= HEALTH_SCORE_FAIR else LOSS
