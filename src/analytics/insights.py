"""Motore di insight: punteggi sintetici e interpretazione automatica del portafoglio.

Tutto è deterministico e calcolato sui dati: nessun testo inventato.
Le soglie dei punteggi (0-100) sono euristiche dichiarate nei singoli score.
"""

import pandas as pd

from src.i18n import t
from src.portfolio import Portfolio, weights_series

TRADING_DAYS = 252


def _scale(value: float, low: float, high: float) -> float:
    """Mappa value da [low, high] a [0, 100], con clipping."""
    if value != value:  # NaN
        return float("nan")
    return float(min(100.0, max(0.0, (value - low) / (high - low) * 100)))


def risk_contributions(returns: pd.DataFrame, portfolio: Portfolio) -> pd.Series:
    """Quota della varianza totale attribuibile a ogni titolo (somma = 1)."""
    weights = weights_series(portfolio)
    cov = returns[weights.index].cov()
    total_variance = float(weights @ cov @ weights)
    if total_variance == 0:
        return pd.Series(dtype=float)
    marginal = cov @ weights
    contributions = weights * marginal / total_variance
    return contributions.sort_values(ascending=False)


def concentration_score(portfolio: Portfolio) -> float:
    """0 = perfettamente equipesato, 100 = tutto su un titolo (indice HHI normalizzato)."""
    weights = weights_series(portfolio)
    n = len(weights)
    if n <= 1:
        return 100.0
    hhi = float((weights**2).sum())
    return _scale(hhi, 1 / n, 1.0)


def radar_scores(
    annual_volatility: float,
    portfolio: Portfolio,
    drawdown: float,
    avg_correlation: float,
) -> dict[str, float]:
    """Quattro assi di rischio, ciascuno 0 (tranquillo) - 100 (estremo)."""
    return {
        "Volatility": _scale(annual_volatility, 0.10, 0.60),
        "Concentration": concentration_score(portfolio),
        "Drawdown": _scale(-drawdown, 0.0, 0.50),
        "Correlation": _scale(avg_correlation, 0.0, 1.0),
    }


def portfolio_risk_score(scores: dict[str, float]) -> int:
    """Punteggio di rischio complessivo 0-100 (media degli assi disponibili)."""
    valid = [s for s in scores.values() if s == s]
    return round(sum(valid) / len(valid)) if valid else 0


def dna_scores(
    fundamentals: pd.DataFrame,
    portfolio: Portfolio,
    annual_volatility: float,
    avg_correlation: float,
) -> dict[str, float]:
    """Il 'DNA' del portafoglio: Growth, Quality, Value, Risk in 0-100.

    Medie ponderate dei fondamentali. Soglie: crescita ricavi 0-40%,
    margine netto 0-35%, debt/equity 0-200, P/E 10-60, P/S 2-20.
    """
    weights = weights_series(portfolio).reindex(fundamentals.index).fillna(0.0)
    if weights.sum() == 0:
        return {}
    weights = weights / weights.sum()

    def weighted(column: str) -> float:
        values = fundamentals[column]
        mask = values.notna()
        if not mask.any():
            return float("nan")
        return float((values[mask] * weights[mask]).sum() / weights[mask].sum())

    growth = _scale(weighted("revenue_growth"), 0.0, 0.40)
    quality_parts = [
        _scale(weighted("net_margin"), 0.0, 0.35),
        100 - _scale(weighted("debt_to_equity"), 0.0, 200.0),
    ]
    quality = sum(p for p in quality_parts if p == p) / max(
        1, sum(1 for p in quality_parts if p == p)
    )
    value_parts = [
        100 - _scale(weighted("pe"), 10.0, 60.0),
        100 - _scale(weighted("ps"), 2.0, 20.0),
    ]
    value = sum(p for p in value_parts if p == p) / max(1, sum(1 for p in value_parts if p == p))
    risk_parts = [
        _scale(annual_volatility, 0.10, 0.60),
        concentration_score(portfolio),
        _scale(avg_correlation, 0.0, 1.0),
    ]
    risk = sum(p for p in risk_parts if p == p) / max(1, sum(1 for p in risk_parts if p == p))
    return {"Growth": growth, "Quality": quality, "Value": value, "Risk": risk}


def dna_label(dna: dict[str, float]) -> str:
    if not dna:
        return ""
    growth, value, risk = dna.get("Growth", 0), dna.get("Value", 0), dna.get("Risk", 0)
    if growth >= 70 and risk >= 60:
        return t("dna.aggressive_growth")
    if growth >= 70:
        return t("dna.growth")
    if value >= 60:
        return t("dna.value")
    if risk <= 35:
        return t("dna.defensive")
    return t("dna.balanced")


def stock_scores(row: pd.Series, annual_volatility: float) -> dict[str, float]:
    """Punteggi 0-100 di un singolo titolo dai suoi fondamentali + volatilità."""

    def mean_valid(parts: list[float]) -> float:
        valid = [p for p in parts if p == p]
        return sum(valid) / len(valid) if valid else float("nan")

    growth = mean_valid(
        [
            _scale(row.get("revenue_growth"), 0.0, 0.40),
            _scale(row.get("earnings_growth"), 0.0, 0.60),
        ]
    )
    quality = mean_valid(
        [
            _scale(row.get("net_margin"), 0.0, 0.35),
            _scale(row.get("operating_margin"), 0.0, 0.45),
            100 - _scale(row.get("debt_to_equity"), 0.0, 200.0),
        ]
    )
    valuation = mean_valid(
        [
            100 - _scale(row.get("pe"), 10.0, 60.0),
            100 - _scale(row.get("ps"), 2.0, 20.0),
            100 - _scale(row.get("ev_ebitda"), 8.0, 40.0),
        ]
    )
    risk = _scale(annual_volatility, 0.15, 0.80)

    scores = {"Growth": growth, "Quality": quality, "Valuation": valuation, "Risk": risk}
    # overall: growth/quality/valuation pesano positivo, il rischio sottrae
    weighted = [
        (scores["Growth"], 0.35),
        (scores["Quality"], 0.35),
        (scores["Valuation"], 0.20),
        (100 - scores["Risk"], 0.10),
    ]
    valid = [(s, w) for s, w in weighted if s == s]
    scores["Overall"] = (
        sum(s * w for s, w in valid) / sum(w for _, w in valid) if valid else float("nan")
    )
    return scores


def monthly_returns(daily_returns: pd.Series, months: int = 12) -> pd.Series:
    """Rendimenti mensili composti degli ultimi `months` mesi."""
    monthly = daily_returns.resample("ME").apply(lambda s: float((1 + s).prod() - 1))
    return monthly.tail(months)


DEFENSIVE_SECTORS = ("Healthcare", "Consumer Defensive", "Utilities")


def reduce_position(portfolio: Portfolio, ticker: str, reduction: float = 0.5) -> Portfolio:
    """Riduce il peso di `ticker` di `reduction` e rinormalizza: la quota
    liberata si redistribuisce proporzionalmente sugli altri titoli."""
    weights = weights_series(portfolio).copy()
    if ticker not in weights.index:
        raise ValueError(f"Ticker '{ticker}' not in the portfolio")
    weights[ticker] *= 1 - reduction
    weights = weights / weights.sum()
    return [{"ticker": t, "weight": float(w)} for t, w in weights.items() if w > 0]


def equal_weight_portfolio(portfolio: Portfolio) -> Portfolio:
    """Stesso portafoglio, pesi uguali su tutti i titoli."""
    n = len(portfolio)
    return [{"ticker": p["ticker"], "weight": 1 / n} for p in portfolio]


def usd_exposure(portfolio: Portfolio) -> float:
    """Quota del portafoglio quotata in USD (0-1), dedotta dal suffisso ticker."""
    from src.data.fx import is_usd_listing

    return float(sum(p["weight"] for p in portfolio if is_usd_listing(p["ticker"])))


def health_breakdown(
    dna: dict[str, float],
    radar: dict[str, float],
    usd_weight: float,
) -> dict[str, float]:
    """Le sei componenti dell'Health Score, ciascuna 0 (male) - 100 (bene).

    Valuta: sotto il 50% di esposizione USD punteggio pieno; al 100% USD
    punteggio zero — per un investitore in euro è rischio cambio puro.
    """
    return {
        "Diversification": 100 - radar.get("Correlation", float("nan")),
        "Concentration": 100 - radar.get("Concentration", float("nan")),
        "Volatility": 100 - radar.get("Volatility", float("nan")),
        "Currency": 100 - _scale(usd_weight, 0.5, 1.0),
        "Drawdown": 100 - radar.get("Drawdown", float("nan")),
        "Quality": dna.get("Quality", float("nan")),
    }


def portfolio_health_score(breakdown: dict[str, float]) -> int:
    """Punteggio di salute 0-100: media delle sei componenti disponibili."""
    valid = [score for score in breakdown.values() if score == score]
    if not valid:
        return 0
    return round(sum(valid) / len(valid))


def executive_summary(
    period: str,
    cumulative_return: float,
    breakdown: dict[str, float],
    contributions: pd.Series,
    avg_correlation: float,
    usd_weight: float,
    drawdown: float,
    beta: float,
    benchmark: str,
) -> str:
    """Sintesi da analista in un paragrafo, composta solo dalle metriche calcolate."""
    parts = [t("exec.ret", period=period, ret=f"{cumulative_return:+.1%}")]

    if avg_correlation == avg_correlation:
        corr = f"{avg_correlation:.2f}"
        if avg_correlation > 0.6:
            parts.append(t("exec.corr_weak", corr=corr))
        elif avg_correlation < 0.3:
            parts.append(t("exec.corr_good", corr=corr))
        else:
            parts.append(t("exec.corr_avg", corr=corr))

    if len(contributions) >= 2 and contributions.iloc[0] > max(0.40, 1.5 / len(contributions)):
        parts.append(
            t(
                "exec.risk_conc",
                ticker=contributions.index[0],
                share=f"{contributions.iloc[0]:.0%}",
            )
        )

    if usd_weight >= 0.7:
        parts.append(t("exec.usd", share=f"{usd_weight:.0%}"))

    if drawdown == drawdown:
        if drawdown < -0.25:
            parts.append(t("exec.dd_high", dd=f"{-drawdown:.0%}"))
        elif drawdown > -0.10:
            parts.append(t("exec.dd_low", dd=f"{-drawdown:.0%}"))

    if beta == beta:
        if beta > 1.15:
            parts.append(t("exec.beta_high", beta=f"{beta:.2f}", benchmark=benchmark))
        elif beta < 0.85:
            parts.append(t("exec.beta_low", beta=f"{beta:.2f}", benchmark=benchmark))

    return " ".join(parts)


def find_problems(
    portfolio: Portfolio,
    fundamentals: pd.DataFrame,
    contributions: pd.Series,
    avg_correlation: float,
    radar: dict[str, float],
) -> list[str]:
    """Problemi concreti del portafoglio, in ordine di importanza."""
    problems = []
    weights = weights_series(portfolio).sort_values(ascending=False)

    if len(weights) > 1 and weights.iloc[0] > 0.25:
        problems.append(
            t("prob.concentration", ticker=weights.index[0], weight=f"{weights.iloc[0]:.0%}")
        )
    if len(contributions) >= 2 and contributions.iloc[0] > max(0.40, 1.5 / len(contributions)):
        problems.append(
            t(
                "prob.risk_driver",
                ticker=contributions.index[0],
                share=f"{contributions.iloc[0]:.0%}",
            )
        )
    if avg_correlation == avg_correlation and avg_correlation > 0.6:
        problems.append(t("prob.correlation", corr=f"{avg_correlation:.0%}"))
    if "dividend_yield" in fundamentals.columns:
        dy = fundamentals["dividend_yield"]
        mask = dy.notna()
        if mask.any():
            weighted_yield = float(
                (dy[mask] * weights.reindex(fundamentals.index)[mask]).sum()
                / weights.reindex(fundamentals.index)[mask].sum()
            )
            if weighted_yield < 1.0:  # in punti percentuali
                problems.append(t("prob.dividend", dy=f"{weighted_yield:.1f}"))
    if radar.get("Volatility", 0) > 70:
        problems.append(t("prob.volatility"))
    return problems


def find_opportunities(
    portfolio: Portfolio,
    fundamentals: pd.DataFrame,
    stock_score_fn=None,
) -> list[str]:
    """Opportunità: settori difensivi scoperti e titoli a valutazione interessante."""
    opportunities = []

    if "sector" in fundamentals.columns:
        held_sectors = set(fundamentals["sector"].dropna())
        missing = [s for s in DEFENSIVE_SECTORS if s not in held_sectors]
        if missing:
            opportunities.append(t("opp.defensive_sectors", sectors=", ".join(missing)))

    if {"pe", "ps"}.issubset(fundamentals.columns):
        cheap = fundamentals[
            (fundamentals["pe"].notna()) & (fundamentals["pe"] < 25) & (fundamentals["ps"] < 6)
        ]
        for ticker in cheap.index[:2]:
            opportunities.append(
                t(
                    "opp.cheap",
                    ticker=ticker,
                    pe=f"{cheap.loc[ticker, 'pe']:.0f}",
                    ps=f"{cheap.loc[ticker, 'ps']:.1f}",
                )
            )

    if not opportunities:
        opportunities.append(t("opp.none"))
    return opportunities


def generate_suggestions(
    dna: dict[str, float],
    radar: dict[str, float],
    contributions: pd.Series,
) -> list[str]:
    """Osservazioni descrittive derivate dalle stesse regole dei punteggi.

    Formulazione deliberatamente NON prescrittiva (nessun imperativo, nessuna
    raccomandazione su strumenti): descrive ciò che le metriche evidenziano e
    cita, dove utile, prassi prudenziali generali. Vedi docs/ENTERPRISE.md §2.
    """
    suggestions = []
    if radar.get("Concentration", 0) > 60 and len(contributions):
        suggestions.append(t("sugg.concentration", ticker=contributions.index[0]))
    if radar.get("Correlation", 0) > 60:
        suggestions.append(t("sugg.correlation"))
    if radar.get("Volatility", 0) > 70:
        suggestions.append(t("sugg.volatility"))
    if dna.get("Value", 100) < 30:
        suggestions.append(t("sugg.multiples"))
    if not suggestions:
        suggestions.append(t("sugg.balanced"))
    return suggestions


def generate_insights(
    period_label: str,
    cumulative_return: float,
    contributions: pd.Series,
    avg_correlation: float,
    drawdown: float,
    beta: float,
    benchmark: str,
) -> list[str]:
    """Frasi di analisi, tutte derivate dai numeri calcolati (lingua da i18n)."""
    insights = [t("ins.ret", ret=f"{cumulative_return:+.1%}", period=period_label)]
    if len(contributions) >= 2:
        top2 = contributions.head(2)
        insights.append(
            t("ins.top2", t1=top2.index[0], t2=top2.index[1], share=f"{top2.sum():.0%}")
        )
    if avg_correlation == avg_correlation:
        if avg_correlation > 0.6:
            insights.append(t("ins.corr_high", corr=f"{avg_correlation:.2f}"))
        elif avg_correlation < 0.3:
            insights.append(t("ins.corr_good", corr=f"{avg_correlation:.2f}"))
    if drawdown == drawdown and drawdown < -0.15:
        insights.append(t("ins.drawdown", dd=f"{drawdown:.0%}"))
    if beta == beta:
        if beta > 1.15:
            insights.append(t("ins.beta_high", beta=f"{beta:.2f}", benchmark=benchmark))
        elif beta < 0.85:
            insights.append(t("ins.beta_low", beta=f"{beta:.2f}", benchmark=benchmark))
    return insights
