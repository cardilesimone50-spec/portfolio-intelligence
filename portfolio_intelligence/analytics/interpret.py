"""Plain-language interpretation of the metrics ("so what?").

Honesty rules: bands based on declared references (historical equity norms,
conventional correction/bear-market thresholds) and percentiles computed ONLY
against the Nasdaq-100 universe we actually hold in the database. No comparison
against datasets we do not own.

Tutte le frasi passano dal catalogo i18n: la lingua segue set_language().
"""

import pandas as pd

from portfolio_intelligence.config import (
    BETA_HIGH,
    BETA_LOW,
    CORRELATION_ELEVATED,
    CORRELATION_HIGH,
    CORRELATION_LOW,
    DRAWDOWN_INTERPRET_BEAR,
    DRAWDOWN_INTERPRET_CORRECTION,
    DRAWDOWN_INTERPRET_NORMAL,
    SHARPE_GOOD,
    SHARPE_INLINE,
    SHARPE_MODEST,
    SHARPE_NEGATIVE,
    SORTINO_DOWNSIDE_RATIO,
    SORTINO_UPSIDE_RATIO,
    VOLATILITY_HIGH,
    VOLATILITY_LOW,
    VOLATILITY_MID,
)
from portfolio_intelligence.formatting import ui_pct
from portfolio_intelligence.i18n import t


def universe_percentile(value: float, universe: pd.Series) -> float:
    """Fraction of the universe with a value below `value` (0-1)."""
    valid = universe.dropna()
    if len(valid) == 0 or value != value:
        return float("nan")
    return float((valid < value).mean())


def interpret_volatility(annual_vol: float, universe_vols: pd.Series | None = None) -> str:
    if annual_vol != annual_vol:
        return ""
    if annual_vol < VOLATILITY_LOW:
        text = t("vol.low")
    elif annual_vol < VOLATILITY_MID:
        text = t("vol.mid")
    elif annual_vol < VOLATILITY_HIGH:
        text = t("vol.high")
    else:
        text = t("vol.extreme")
    if universe_vols is not None:
        pct = universe_percentile(annual_vol, universe_vols)
        if pct == pct:
            text += t("vol.percentile", pct=ui_pct(1 - pct, 0))
    return text


def interpret_sharpe(sharpe: float) -> str:
    if sharpe != sharpe:
        return ""
    if sharpe < SHARPE_NEGATIVE:
        return t("sharpe.negative")
    if sharpe < SHARPE_MODEST:
        return t("sharpe.modest")
    if sharpe < SHARPE_INLINE:
        return t("sharpe.inline")
    if sharpe < SHARPE_GOOD:
        return t("sharpe.good")
    return t("sharpe.exceptional")


def interpret_sortino(sortino: float, sharpe: float) -> str:
    if sortino != sortino or sharpe != sharpe or sharpe == 0:
        return ""
    if sortino > sharpe * SORTINO_UPSIDE_RATIO:
        return t("sortino.upside")
    if sortino < sharpe * SORTINO_DOWNSIDE_RATIO:
        return t("sortino.downside")
    return t("sortino.symmetric")


def interpret_drawdown(drawdown: float) -> str:
    if drawdown != drawdown:
        return ""
    if drawdown > DRAWDOWN_INTERPRET_NORMAL:
        return t("dd.normal")
    if drawdown > DRAWDOWN_INTERPRET_CORRECTION:
        return t("dd.correction")
    if drawdown > DRAWDOWN_INTERPRET_BEAR:
        return t("dd.bear")
    return t("dd.severe")


def interpret_beta(beta: float, benchmark: str) -> str:
    if beta != beta:
        return ""
    if beta < BETA_LOW:
        return t("beta.defensive", benchmark=benchmark)
    if beta <= BETA_HIGH:
        return t("beta.inline", benchmark=benchmark)
    return t("beta.amplify", benchmark=benchmark)


def interpret_correlation(avg_correlation: float) -> str:
    if avg_correlation != avg_correlation:
        return ""
    if avg_correlation > CORRELATION_HIGH:
        return t("corr.identical")
    if avg_correlation > CORRELATION_ELEVATED:
        return t("corr.close")
    if avg_correlation > CORRELATION_LOW:
        return t("corr.average")
    return t("corr.independent")
