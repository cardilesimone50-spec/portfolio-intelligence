"""Motore di insight: punteggi sintetici e interpretazione automatica del portafoglio.

Tutto è deterministico e calcolato sui dati: nessun testo inventato.
Le soglie dei punteggi (0-100) sono euristiche dichiarate nei singoli score.
"""

import pandas as pd

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
        return "Aggressive growth profile"
    if growth >= 70:
        return "Growth profile"
    if value >= 60:
        return "Value profile"
    if risk <= 35:
        return "Defensive profile"
    return "Balanced profile"


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
    parts = [f"Over the period ({period}) the portfolio returned {cumulative_return:+.1%}."]

    if avg_correlation == avg_correlation:
        if avg_correlation > 0.6:
            parts.append(
                "Diversification is weak: the holdings move very similarly "
                f"(average correlation {avg_correlation:.2f})."
            )
        elif avg_correlation < 0.3:
            parts.append(
                f"The portfolio is well diversified (average correlation {avg_correlation:.2f})."
            )
        else:
            parts.append(f"Diversification is average (correlation {avg_correlation:.2f}).")

    if len(contributions) >= 2 and contributions.iloc[0] > max(0.40, 1.5 / len(contributions)):
        parts.append(
            f"Risk is concentrated: {contributions.index[0]} alone drives "
            f"{contributions.iloc[0]:.0%} of total variability."
        )

    if usd_weight >= 0.7:
        parts.append(
            f"US-dollar exposure is high ({usd_weight:.0%} of capital): "
            "the euro result also depends on the EUR/USD rate."
        )

    if drawdown == drawdown:
        if drawdown < -0.25:
            parts.append(
                "Historical downside risk is above average: over the period the "
                f"portfolio fell as much as {-drawdown:.0%} from its peak."
            )
        elif drawdown > -0.10:
            parts.append(f"Drops from the peak stayed contained (max {-drawdown:.0%}).")

    if beta == beta:
        if beta > 1.15:
            parts.append(
                f"With a beta of {beta:.2f} versus {benchmark}, the portfolio "
                "amplifies market moves."
            )
        elif beta < 0.85:
            parts.append(
                f"With a beta of {beta:.2f} versus {benchmark}, the portfolio "
                "is more defensive than the market."
            )

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
            f"**{weights.index[0]}** is **{weights.iloc[0]:.0%}** of the "
            "portfolio: high concentration risk."
        )
    if len(contributions) >= 2 and contributions.iloc[0] > max(0.40, 1.5 / len(contributions)):
        problems.append(
            f"**{contributions.index[0]}** drives **{contributions.iloc[0]:.0%} of total risk**."
        )
    if avg_correlation == avg_correlation and avg_correlation > 0.6:
        problems.append(
            f"Average correlation **{avg_correlation:.0%}**: the holdings move "
            "together, the portfolio rides a single engine."
        )
    if "dividend_yield" in fundamentals.columns:
        dy = fundamentals["dividend_yield"]
        mask = dy.notna()
        if mask.any():
            weighted_yield = float(
                (dy[mask] * weights.reindex(fundamentals.index)[mask]).sum()
                / weights.reindex(fundamentals.index)[mask].sum()
            )
            if weighted_yield < 1.0:  # in punti percentuali
                problems.append(
                    f"Dividend yield **{weighted_yield:.1f}%**, below the "
                    "market average: the portfolio generates little income."
                )
    if radar.get("Volatility", 0) > 70:
        problems.append("Elevated volatility versus a balanced portfolio.")
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
            opportunities.append(
                f"Uncovered defensive sectors (**{', '.join(missing)}**): "
                "adding them would reduce reliance on the tech cycle."
            )

    if {"pe", "ps"}.issubset(fundamentals.columns):
        cheap = fundamentals[
            (fundamentals["pe"].notna()) & (fundamentals["pe"] < 25) & (fundamentals["ps"] < 6)
        ]
        for ticker in cheap.index[:2]:
            opportunities.append(
                f"Among the holdings, **{ticker}** has the lowest multiples "
                f"(P/E {cheap.loc[ticker, 'pe']:.0f}, P/S "
                f"{cheap.loc[ticker, 'ps']:.1f})."
            )

    if not opportunities:
        opportunities.append(
            "No obvious gaps against the monitored rules (defensive sectors, valuations)."
        )
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
        suggestions.append(
            f"Concentration is high: **{contributions.index[0]}** dominates "
            "risk. A common prudential guideline treats a single-stock weight "
            "above 25% as critical."
        )
    if radar.get("Correlation", 0) > 60:
        suggestions.append(
            "The holdings tend to move together: instruments from less-correlated "
            "sectors or regions generally reduce overall variability."
        )
    if radar.get("Volatility", 0) > 70:
        suggestions.append(
            "Volatility is high: in general, lower-beta components dampen the "
            "amplitude of a portfolio's swings."
        )
    if dna.get("Value", 100) < 30:
        suggestions.append(
            "The portfolio's average multiples are high (elevated P/E and P/S): "
            "the price embeds significant growth expectations."
        )
    if not suggestions:
        suggestions.append(
            "The portfolio looks balanced against the monitored rules: "
            "concentration, correlation, volatility and multiples."
        )
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
    """Frasi di analisi in italiano, tutte derivate dai numeri calcolati."""
    insights = [
        f"The portfolio returned **{cumulative_return:+.1%}** over the period ({period_label})."
    ]
    if len(contributions) >= 2:
        top2 = contributions.head(2)
        insights.append(
            f"**{top2.index[0]}** and **{top2.index[1]}** account for "
            f"**{top2.sum():.0%} of the portfolio's total risk**."
        )
    if avg_correlation == avg_correlation:
        if avg_correlation > 0.6:
            insights.append(
                f"Your holdings are tightly linked (average correlation "
                f"**{avg_correlation:.2f}**): diversification is weak."
            )
        elif avg_correlation < 0.3:
            insights.append(
                f"Good diversification: average correlation **{avg_correlation:.2f}**."
            )
    if drawdown == drawdown and drawdown < -0.15:
        insights.append(
            f"Over the period the portfolio suffered a maximum drop of "
            f"**{drawdown:.0%}** from its peak."
        )
    if beta == beta:
        if beta > 1.15:
            insights.append(f"Beta **{beta:.2f}** vs {benchmark}: you amplify market moves.")
        elif beta < 0.85:
            insights.append(
                f"Beta **{beta:.2f}** vs {benchmark}: you are more defensive than the market."
            )
    return insights
