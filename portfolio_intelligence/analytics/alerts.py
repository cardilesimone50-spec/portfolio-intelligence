"""Automatic alerts: conditions that deserve immediate attention."""

import pandas as pd

from portfolio_intelligence.config import (
    CONCENTRATION_FAIR_SHARE_MULT,
    CONCENTRATION_MIN_ABS,
    CORRELATION_HIGH,
    DAILY_MOVE_ALERT,
    DRAWDOWN_ALERT,
)
from portfolio_intelligence.formatting import ui_num, ui_pct
from portfolio_intelligence.i18n import t
from portfolio_intelligence.portfolio import Portfolio, weights_series


def evaluate_alerts(
    returns: pd.DataFrame,
    portfolio: Portfolio,
    contributions: pd.Series,
    avg_correlation: float,
    drawdown: float,
) -> list[str]:
    """List of alerts (ready-to-display strings); empty if all is well."""
    alerts = []

    # fires if the top holding exceeds 1.5x its fair share (1/n), and at least
    # 40%: with two equally weighted holdings, 50% is physiological
    if len(contributions):
        fair_share = 1 / len(contributions)
        threshold = max(CONCENTRATION_MIN_ABS, CONCENTRATION_FAIR_SHARE_MULT * fair_share)
        if contributions.iloc[0] > threshold:
            alerts.append(
                t(
                    "alert.risk_driver",
                    ticker=contributions.index[0],
                    share=ui_pct(contributions.iloc[0], 0),
                )
            )

    if avg_correlation == avg_correlation and avg_correlation > CORRELATION_HIGH:
        alerts.append(t("alert.correlation", corr=ui_num(avg_correlation, 2)))

    if drawdown == drawdown and drawdown < DRAWDOWN_ALERT:
        alerts.append(t("alert.drawdown", dd=ui_pct(drawdown, 0)))

    # last available session move
    weights = weights_series(portfolio)
    last_day = returns[weights.index].iloc[-1]
    day_move = float((last_day * weights).sum())
    if day_move < DAILY_MOVE_ALERT:
        contribution_today = last_day * weights
        worst = contribution_today.idxmin()
        alerts.append(
            t(
                "alert.last_session",
                move=ui_pct(day_move, 1, signed=True),
                ticker=str(worst),
                contrib=ui_pct(float(contribution_today[worst]), 1, signed=True),
            )
        )

    return alerts
