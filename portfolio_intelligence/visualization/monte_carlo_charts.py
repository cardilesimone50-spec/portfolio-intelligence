"""Fan chart della simulazione Monte Carlo (Altair)."""

import altair as alt
import pandas as pd

from portfolio_intelligence.analytics.monte_carlo import MonteCarloResult
from portfolio_intelligence.i18n import t

FAN_COLOR = "#1E40AF"  # colore del marchio: un'unica tinta, intensità diverse per le fasce
BASELINE_COLOR = "#64748b"

# Euro con il punto come separatore delle migliaia (convenzione italiana)
_EUR_LABEL = "replace(format(datum.value, ',.0f'), /,/g, '.') + ' €'"


def _eur(value: float) -> str:
    return f"{value:,.0f} €".replace(",", ".")


def fan_data(result: MonteCarloResult) -> pd.DataFrame:
    """Una riga per mese: percentili numerici e loro etichette in euro per il tooltip."""
    df = result.paths.reset_index()
    months = (df["years"] * 12).round().astype(int)
    df["when"] = [
        t("mc.month0") if m == 0 else t("mc.when", years=m // 12, months=m % 12) for m in months
    ]
    for col in ("p10", "p25", "p50", "p75", "p90"):
        df[f"{col}_eur"] = df[col].map(_eur)
    return df


def fan_chart(result: MonteCarloResult, height: int = 320) -> alt.Chart:
    """Fasce p10-p90 (chiara) e p25-p75 (più scura), mediana p50 e valore iniziale."""
    df = fan_data(result)
    x = alt.X(
        "years:Q",
        title=t("mc.axis_years"),
        scale=alt.Scale(domain=[0, result.horizon_years], nice=False),
        axis=alt.Axis(tickCount=result.horizon_years, format="d", grid=False),
    )
    y_axis = alt.Axis(labelExpr=_EUR_LABEL, title=None, grid=True, gridOpacity=0.4)
    tooltip = [
        alt.Tooltip("when:N", title=t("mc.tt_when")),
        alt.Tooltip("p90_eur:N", title=t("mc.tt_p90")),
        alt.Tooltip("p75_eur:N", title=t("mc.tt_p75")),
        alt.Tooltip("p50_eur:N", title=t("mc.tt_p50")),
        alt.Tooltip("p25_eur:N", title=t("mc.tt_p25")),
        alt.Tooltip("p10_eur:N", title=t("mc.tt_p10")),
    ]
    base = alt.Chart(df).encode(x=x)
    wide = base.mark_area(color=FAN_COLOR, opacity=0.14).encode(
        y=alt.Y("p10:Q", axis=y_axis, scale=alt.Scale(zero=False)), y2="p90:Q"
    )
    core = base.mark_area(color=FAN_COLOR, opacity=0.30).encode(y="p25:Q", y2="p75:Q")
    median = base.mark_line(color=FAN_COLOR, strokeWidth=2.5).encode(y="p50:Q")
    start = (
        alt.Chart(pd.DataFrame({"value": [result.initial_value]}))
        .mark_rule(color=BASELINE_COLOR, strokeDash=[4, 4])
        .encode(y="value:Q")
    )
    # livello invisibile su tutta l'altezza: il tooltip compare ovunque lungo l'asse x
    hover = base.mark_rule(opacity=0, strokeWidth=12).encode(
        y="p90:Q", y2="p10:Q", tooltip=tooltip
    )
    return (wide + core + median + start + hover).properties(height=height)
