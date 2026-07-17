"""Pipeline di analisi condivisa: dai prezzi al quadro completo del portafoglio.

Funzione pura (niente Streamlit, niente rete): app.py scarica i dati e delega
qui tutti i calcoli. Così il cuore analitico è unit-testabile e riusabile
(CLI, batch, API future).
"""

import pandas as pd

from src.analytics.insights import (
    dna_scores,
    health_breakdown,
    portfolio_health_score,
    portfolio_risk_score,
    radar_scores,
    risk_contributions,
    usd_exposure,
)
from src.analytics.performance import (
    annualized_geometric_return,
    beta_alpha,
    max_drawdown,
    value_at_risk,
)
from src.portfolio import Portfolio
from src.portfolio.returns import compute_daily_returns, portfolio_daily_returns
from src.portfolio.risk import average_pairwise_correlation, portfolio_volatility

TRADING_DAYS = 252


def analyze_portfolio(
    prices: pd.DataFrame,
    bench_prices: pd.DataFrame,
    portfolio: Portfolio,
    fund: pd.DataFrame,
    benchmark: str = "QQQ",
) -> dict:
    """Tutte le metriche del check-up a partire da prezzi già scaricati.

    `prices` e `bench_prices` sono listini giornalieri (già convertiti in EUR
    se richiesto); `fund` è la tabella fondamentali (può avere colonne NaN).
    Restituisce il dict `computed` usato da tutte le viste.
    """
    returns = compute_daily_returns(prices)

    pf_daily = portfolio_daily_returns(returns, portfolio)
    pf_value = (1 + pf_daily).cumprod()
    cum_return = float(pf_value.iloc[-1] - 1)

    annual_ret = annualized_geometric_return(pf_daily)
    annual_vol = portfolio_volatility(returns, portfolio) * TRADING_DAYS**0.5
    drawdown = max_drawdown(pf_value)
    var_95 = value_at_risk(pf_daily)
    min_periods = max(15, min(60, len(returns) // 2))
    avg_corr = average_pairwise_correlation(returns, min_periods=min_periods)

    bench_daily = compute_daily_returns(bench_prices)[benchmark]
    beta, alpha = beta_alpha(pf_daily, bench_daily)

    contributions = risk_contributions(returns, portfolio)
    radar = radar_scores(annual_vol, portfolio, drawdown, avg_corr)
    risk_score = portfolio_risk_score(radar)

    dna = dna_scores(fund, portfolio, annual_vol, avg_corr)
    usd_weight = usd_exposure(portfolio)
    breakdown = health_breakdown(dna, radar, usd_weight)
    health = portfolio_health_score(breakdown)

    return {
        "returns": returns,
        "prices": prices,
        "pf_daily": pf_daily,
        "pf_value": pf_value,
        "bench_daily": bench_daily,
        "annual_ret": annual_ret,
        "annual_vol": annual_vol,
        "drawdown": drawdown,
        "avg_corr": avg_corr,
        "var_95": var_95,
        "beta": beta,
        "alpha": alpha,
        "min_periods": min_periods,
        "cum_return": cum_return,
        "risk_score": risk_score,
        "contributions": contributions,
        "radar": radar,
        "fund": fund,
        "dna": dna,
        "health": health,
        "breakdown": breakdown,
        "usd_weight": usd_weight,
    }
