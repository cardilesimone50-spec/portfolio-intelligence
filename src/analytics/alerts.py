"""Automatic alerts: conditions that deserve immediate attention."""

import pandas as pd

from src.i18n import t
from src.portfolio import Portfolio, weights_series


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
        threshold = max(0.40, 1.5 * fair_share)
        if contributions.iloc[0] > threshold:
            alerts.append(
                t(
                    "alert.risk_driver",
                    ticker=contributions.index[0],
                    share=f"{contributions.iloc[0]:.0%}",
                )
            )

    if avg_correlation == avg_correlation and avg_correlation > 0.75:
        alerts.append(t("alert.correlation", corr=f"{avg_correlation:.2f}"))

    if drawdown == drawdown and drawdown < -0.30:
        alerts.append(t("alert.drawdown", dd=f"{drawdown:.0%}"))

    # last available session move
    weights = weights_series(portfolio)
    last_day = returns[weights.index].iloc[-1]
    day_move = float((last_day * weights).sum())
    if day_move < -0.02:
        contribution_today = last_day * weights
        worst = contribution_today.idxmin()
        alerts.append(
            t(
                "alert.last_session",
                move=f"{day_move:+.1%}",
                ticker=str(worst),
                contrib=f"{float(contribution_today[worst]):+.1%}",
            )
        )

    return alerts
