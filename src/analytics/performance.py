"""Metriche di performance: statistiche annualizzate, Sharpe, drawdown."""

import pandas as pd

from src.portfolio import Portfolio
from src.portfolio.returns import portfolio_daily_returns, portfolio_expected_return
from src.portfolio.risk import portfolio_volatility

TRADING_DAYS = 252


def per_ticker_annualized_stats(
    returns: pd.DataFrame, trading_days: int = TRADING_DAYS
) -> pd.DataFrame:
    """Rendimento e volatilità annualizzati per ciascun ticker, dai rendimenti giornalieri."""
    return pd.DataFrame(
        {
            "annual_return": returns.mean() * trading_days,
            "annual_volatility": returns.std() * trading_days**0.5,
        }
    )


def annualized_geometric_return(
    daily_returns: pd.Series, trading_days: int = TRADING_DAYS
) -> float:
    """Rendimento annualizzato composto (CAGR sul periodo osservato).

    A differenza della media aritmetica × 252, non sovrastima in presenza
    di volatilità: è il numero onesto da mostrare a un investitore.
    """
    valid = daily_returns.dropna()
    if len(valid) == 0:
        return float("nan")
    total = float((1 + valid).prod())
    if total <= 0:
        return -1.0
    return total ** (trading_days / len(valid)) - 1


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


def sortino_ratio(
    returns: pd.DataFrame, portfolio: Portfolio, risk_free_rate: float = 0.0
) -> float:
    """Come lo Sharpe, ma penalizza solo la volatilità al ribasso.

    Downside deviation calcolata su TUTTE le osservazioni (rendimenti positivi
    troncati a zero), come da definizione standard: mediare solo sui giorni
    negativi la sovrastimerebbe.
    """
    daily = portfolio_daily_returns(returns, portfolio)
    if len(daily) == 0:
        return float("nan")
    downside = daily.clip(upper=0.0)
    downside_deviation = float((downside**2).mean() ** 0.5) * TRADING_DAYS**0.5
    annual_return = float(daily.mean()) * TRADING_DAYS
    if downside_deviation == 0:
        return float("inf") if annual_return > risk_free_rate else float("nan")
    return (annual_return - risk_free_rate) / downside_deviation


def value_at_risk(daily_returns: pd.Series, confidence: float = 0.95) -> float:
    """VaR storico giornaliero: perdita che non viene superata nel `confidence`%
    dei giorni, come numero negativo (es. -0.03 = -3%)."""
    valid = daily_returns.dropna()
    if len(valid) < 20:
        return float("nan")
    return float(valid.quantile(1 - confidence))


def beta_alpha(portfolio_returns: pd.Series, benchmark_returns: pd.Series) -> tuple[float, float]:
    """Beta e alpha (annualizzato) del portafoglio rispetto a un benchmark.

    Beta ~1: si muove come il benchmark; >1 amplifica; <1 attenua.
    Alpha: extra-rendimento annuo non spiegato dal benchmark.
    """
    aligned = pd.concat({"pf": portfolio_returns, "bench": benchmark_returns}, axis=1).dropna()
    if len(aligned) < 20:
        return float("nan"), float("nan")
    bench_var = float(aligned["bench"].var())
    if bench_var == 0:
        return float("nan"), float("nan")
    beta = float(aligned["pf"].cov(aligned["bench"])) / bench_var
    alpha = (float(aligned["pf"].mean()) - beta * float(aligned["bench"].mean())) * TRADING_DAYS
    return beta, alpha
