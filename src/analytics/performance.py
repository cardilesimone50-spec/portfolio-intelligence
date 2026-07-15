"""Metriche di performance: statistiche annualizzate, Sharpe, drawdown."""

import pandas as pd

from src.portfolio import Portfolio
from src.portfolio.returns import portfolio_daily_returns
from src.portfolio.risk import portfolio_volatility

TRADING_DAYS = 252


def per_ticker_annualized_stats(
    returns: pd.DataFrame, trading_days: int = TRADING_DAYS
) -> pd.DataFrame:
    """Rendimento annualizzato composto (CAGR) e volatilità annualizzata per ticker.

    Il rendimento usa il composto geometrico, non la media aritmetica × 252: è
    il numero onesto, che non sovrastima in presenza di volatilità.
    """
    return pd.DataFrame(
        {
            "annual_return": returns.apply(
                lambda col: annualized_geometric_return(col, trading_days)
            ),
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
    """Sharpe ratio annualizzato del portafoglio. risk_free_rate è annuale.

    Il numeratore usa il rendimento composto (CAGR), non la media aritmetica
    × 252: è il rendimento che l'investitore incassa davvero e non viene
    sovrastimato in presenza di volatilità.
    """
    daily = portfolio_daily_returns(returns, portfolio)
    annual_return = annualized_geometric_return(daily)
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
    return sortino_from_daily(portfolio_daily_returns(returns, portfolio), risk_free_rate)


def sharpe_from_daily(daily_returns: pd.Series, risk_free_rate: float = 0.0) -> float:
    """Sharpe annualizzato da una serie di rendimenti giornalieri (es. benchmark)."""
    valid = daily_returns.dropna()
    if len(valid) < 2:
        return float("nan")
    annual_volatility = float(valid.std()) * TRADING_DAYS**0.5
    if annual_volatility == 0:
        return float("nan")
    return (annualized_geometric_return(valid) - risk_free_rate) / annual_volatility


def sortino_from_daily(daily_returns: pd.Series, risk_free_rate: float = 0.0) -> float:
    """Sortino annualizzato da una serie di rendimenti giornalieri (es. benchmark)."""
    valid = daily_returns.dropna()
    if len(valid) == 0:
        return float("nan")
    downside = valid.clip(upper=0.0)
    downside_deviation = float((downside**2).mean() ** 0.5) * TRADING_DAYS**0.5
    annual_return = annualized_geometric_return(valid)
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


def expected_shortfall(daily_returns: pd.Series, confidence: float = 0.95) -> float:
    """Expected Shortfall (CVaR) storico: perdita MEDIA nei giorni oltre il VaR.

    Il VaR dice la soglia che non superi nel `confidence`% dei giorni; l'ES
    dice quanto perdi in media quando la superi. È una misura di rischio
    coerente (subadditiva), sempre ≤ del VaR corrispondente.
    """
    valid = daily_returns.dropna()
    if len(valid) < 20:
        return float("nan")
    var = valid.quantile(1 - confidence)
    tail = valid[valid <= var]
    if len(tail) == 0:
        return float(var)
    return float(tail.mean())


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
