"""Plain-language interpretation of the metrics ("so what?").

Honesty rules: bands based on declared references (historical equity norms,
conventional correction/bear-market thresholds) and percentiles computed ONLY
against the Nasdaq-100 universe we actually hold in the database. No comparison
against datasets we do not own.
"""

import pandas as pd


def universe_percentile(value: float, universe: pd.Series) -> float:
    """Fraction of the universe with a value below `value` (0-1)."""
    valid = universe.dropna()
    if len(valid) == 0 or value != value:
        return float("nan")
    return float((valid < value).mean())


def interpret_volatility(annual_vol: float, universe_vols: pd.Series | None = None) -> str:
    if annual_vol != annual_vol:
        return ""
    if annual_vol < 0.12:
        text = "Swings typical of a conservative portfolio."
    elif annual_vol < 0.22:
        text = "Swings typical of a diversified equity portfolio."
    elif annual_vol < 0.35:
        text = "Elevated swings: expect wide moves."
    else:
        text = "Swings of an aggressive single stock, not a portfolio."
    if universe_vols is not None:
        pct = universe_percentile(annual_vol, universe_vols)
        if pct == pct:
            text += f" Less volatile than {1 - pct:.0%} of Nasdaq-100 single stocks."
    return text


def interpret_sharpe(sharpe: float) -> str:
    if sharpe != sharpe:
        return ""
    if sharpe < 0:
        return (
            "Over the period the risk taken was not rewarded: "
            "you returned less than the risk-free rate."
        )
    if sharpe < 0.5:
        return (
            "Modest risk-adjusted return: below the 0.5-1 band typical of a "
            "diversified long-term equity portfolio."
        )
    if sharpe < 1:
        return (
            "In line with what diversified equity has historically paid per unit of risk (0.5-1)."
        )
    if sharpe < 2:
        return "Above the historical norm: each unit of risk was well paid."
    return "Exceptional over the observed period: such values rarely persist."


def interpret_sortino(sortino: float, sharpe: float) -> str:
    if sortino != sortino or sharpe != sharpe or sharpe == 0:
        return ""
    if sortino > sharpe * 1.25:
        return "Volatility skews to the upside: drops weigh less than gains (a good sign)."
    if sortino < sharpe * 0.9:
        return "Volatility is concentrated in the downside: the drops hurt more."
    return "Drops and gains contributed symmetrically to volatility."


def interpret_drawdown(drawdown: float) -> str:
    if drawdown != drawdown:
        return ""
    if drawdown > -0.10:
        return "Within a normal market correction (down to -10%)."
    if drawdown > -0.20:
        return "Between a correction (-10%) and a bear market (-20%)."
    if drawdown > -0.35:
        return "Bear-market territory: drops like this test your discipline."
    return "Severe drawdown: few investors hold through drops this deep without selling."


def interpret_beta(beta: float, benchmark: str) -> str:
    if beta != beta:
        return ""
    if beta < 0.85:
        return f"More defensive than {benchmark}: you dampen market moves."
    if beta <= 1.15:
        return f"You move broadly in line with {benchmark}."
    return f"You amplify {benchmark} moves: steeper rises and falls."


def interpret_correlation(avg_correlation: float) -> str:
    if avg_correlation != avg_correlation:
        return ""
    if avg_correlation > 0.75:
        return "The holdings move almost identically: diversification is only apparent."
    if avg_correlation > 0.6:
        return "The holdings move closely together: the diversification benefit is reduced."
    if avg_correlation > 0.3:
        return "Average diversification for a portfolio within the same market."
    return "The holdings move independently: real, effective diversification."
