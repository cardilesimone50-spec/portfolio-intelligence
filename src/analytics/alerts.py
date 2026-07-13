"""Alert automatici: condizioni che meritano attenzione immediata."""

import pandas as pd

from src.portfolio import Portfolio, weights_series


def evaluate_alerts(
    returns: pd.DataFrame,
    portfolio: Portfolio,
    contributions: pd.Series,
    avg_correlation: float,
    drawdown: float,
) -> list[str]:
    """Lista di alert (stringhe pronte da mostrare); vuota se va tutto bene."""
    alerts = []

    # scatta se il primo titolo supera 1.5 volte la sua quota equa (1/n),
    # e comunque almeno il 40%: con 2 titoli equipesati il 50% è fisiologico
    if len(contributions):
        fair_share = 1 / len(contributions)
        threshold = max(0.40, 1.5 * fair_share)
        if contributions.iloc[0] > threshold:
            alerts.append(
                f"**{contributions.index[0]}** pesa ora il "
                f"**{contributions.iloc[0]:.0%} del rischio totale** del portafoglio."
            )

    if avg_correlation == avg_correlation and avg_correlation > 0.75:
        alerts.append(
            f"Correlazione media salita a **{avg_correlation:.2f}**: "
            "il portafoglio si muove come un titolo solo."
        )

    if drawdown == drawdown and drawdown < -0.30:
        alerts.append(f"Drawdown profondo: **{drawdown:.0%}** dal picco nel periodo analizzato.")

    # movimento dell'ultimo giorno disponibile
    weights = weights_series(portfolio)
    last_day = returns[weights.index].iloc[-1]
    day_move = float((last_day * weights).sum())
    if day_move < -0.02:
        contribution_today = last_day * weights
        worst = contribution_today.idxmin()
        alerts.append(
            f"Ultima seduta: portafoglio **{day_move:+.1%}**. "
            f"Principale responsabile: **{worst}** "
            f"({float(contribution_today[worst]):+.1%} sul totale)."
        )

    return alerts
