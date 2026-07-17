"""Plain-language interpretation of the metrics ("so what?").

Honesty rules: bands based on declared references (historical equity norms,
conventional correction/bear-market thresholds) and percentiles computed ONLY
against the Nasdaq-100 universe we actually hold in the database. No comparison
against datasets we do not own.

Tutte le frasi passano dal catalogo i18n: la lingua segue set_language().
"""

import pandas as pd

from src.i18n import t


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
        text = t("vol.low")
    elif annual_vol < 0.22:
        text = t("vol.mid")
    elif annual_vol < 0.35:
        text = t("vol.high")
    else:
        text = t("vol.extreme")
    if universe_vols is not None:
        pct = universe_percentile(annual_vol, universe_vols)
        if pct == pct:
            text += t("vol.percentile", pct=f"{1 - pct:.0%}")
    return text


def interpret_sharpe(sharpe: float) -> str:
    if sharpe != sharpe:
        return ""
    if sharpe < 0:
        return t("sharpe.negative")
    if sharpe < 0.5:
        return t("sharpe.modest")
    if sharpe < 1:
        return t("sharpe.inline")
    if sharpe < 2:
        return t("sharpe.good")
    return t("sharpe.exceptional")


def interpret_sortino(sortino: float, sharpe: float) -> str:
    if sortino != sortino or sharpe != sharpe or sharpe == 0:
        return ""
    if sortino > sharpe * 1.25:
        return t("sortino.upside")
    if sortino < sharpe * 0.9:
        return t("sortino.downside")
    return t("sortino.symmetric")


def interpret_drawdown(drawdown: float) -> str:
    if drawdown != drawdown:
        return ""
    if drawdown > -0.10:
        return t("dd.normal")
    if drawdown > -0.20:
        return t("dd.correction")
    if drawdown > -0.35:
        return t("dd.bear")
    return t("dd.severe")


def interpret_beta(beta: float, benchmark: str) -> str:
    if beta != beta:
        return ""
    if beta < 0.85:
        return t("beta.defensive", benchmark=benchmark)
    if beta <= 1.15:
        return t("beta.inline", benchmark=benchmark)
    return t("beta.amplify", benchmark=benchmark)


def interpret_correlation(avg_correlation: float) -> str:
    if avg_correlation != avg_correlation:
        return ""
    if avg_correlation > 0.75:
        return t("corr.identical")
    if avg_correlation > 0.6:
        return t("corr.close")
    if avg_correlation > 0.3:
        return t("corr.average")
    return t("corr.independent")
