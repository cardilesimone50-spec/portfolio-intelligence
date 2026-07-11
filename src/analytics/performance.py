"""Metriche di performance: statistiche annualizzate, Sharpe, drawdown."""

import pandas as pd

from src.portfolio import Portfolio
from src.portfolio.returns import portfolio_expected_return
from src.portfolio.risk import portfolio_volatility

TRADING_DAYS = 252


def per_ticker_annualized_stats(returns: pd.DataFrame, trading_days: int = TRADING_DAYS) -> pd.DataFrame:
    """Rendimento e volatilità annualizzati per ciascun ticker, dai rendimenti giornalieri."""
    return pd.DataFrame(
        {
            "annual_return": returns.mean() * trading_days,
            "annual_volatility": returns.std() * trading_days**0.5,
        }
    )


def annualized_sharpe(
    returns: pd.DataFrame, portfolio: Portfolio, risk_free_rate: float = 0.0
) -> float:
    """Sharpe ratio annualizzato del portafoglio. risk_free_rate è annuale."""
    annual_return = portfolio_expected_return(returns, portfolio) * TRADING_DAYS
    annual_volatility = portfolio_volatility(returns, portfolio) * TRADING_DAYS**0.5
    if annual_volatility == 0:
        return float("nan")
    return (annual_return - risk_free_rate) / annual_volatility


def max_drawdown(prices: pd.Series) -> float:
    """Massima perdita dal picco precedente, come numero negativo (es. -0.35 = -35%)."""
    valid = prices.dropna()
    if len(valid) < 2:
        return float("nan")
    drawdowns = valid / valid.cummax() - 1
    return float(drawdowns.min())
