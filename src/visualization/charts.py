"""Grafici Altair riusabili per la dashboard."""

import altair as alt
import pandas as pd

# Palette categorica validata (dataviz skill, light mode)
PALETTE = ["#2a78d6", "#1baf7a", "#eda100", "#008300", "#4a3aa7", "#e34948", "#e87ba4", "#eb6834"]
# Coppia divergente per la correlazione: blu = opposti, grigio = indipendenti, rosso = insieme
DIVERGING = ["#2a78d6", "#f5f5f2", "#e34948"]


def allocation_bars(amounts: dict[str, float]) -> alt.Chart:
    """Barre orizzontali degli importi investiti per titolo."""
    alloc = pd.DataFrame({"ticker": list(amounts), "importo": list(amounts.values())})
    base = alt.Chart(alloc).encode(
        y=alt.Y("ticker:N", sort="-x", title=None),
        x=alt.X("importo:Q", title=None, axis=None),
    )
    bars = base.mark_bar(cornerRadiusEnd=4, height=22).encode(
        color=alt.Color(
            "ticker:N",
            scale=alt.Scale(domain=sorted(amounts), range=PALETTE),
            legend=None,
        )
    )
    labels = base.mark_text(align="left", dx=6).encode(
        text=alt.Text("importo:Q", format=",.0f")
    )
    return (bars + labels).properties(height=42 * len(alloc) + 20)


def correlation_bars(series: pd.Series) -> alt.Chart:
    """Barre orizzontali di correlazione, colore divergente sul segno."""
    df = series.rename("corr").rename_axis("ticker").reset_index()
    base = alt.Chart(df).encode(
        y=alt.Y("ticker:N", sort=None, title=None),
        x=alt.X("corr:Q", title="Correlazione", scale=alt.Scale(domain=[-1, 1])),
    )
    bars = base.mark_bar(cornerRadiusEnd=4, height=18).encode(
        color=alt.Color(
            "corr:Q",
            scale=alt.Scale(domain=[-1, 0, 1], range=DIVERGING),
            legend=None,
        )
    )
    labels = base.mark_text(align="left", dx=6).encode(
        text=alt.Text("corr:Q", format="+.2f")
    )
    return (bars + labels).properties(height=26 * len(df) + 20)


def efficient_frontier_chart(frontier: pd.DataFrame, points: pd.DataFrame) -> alt.Chart:
    """Frontiera efficiente (linea) + portafogli notevoli (punti etichettati).

    `points` ha colonne: nome, annual_return, annual_volatility.
    """
    line = (
        alt.Chart(frontier)
        .mark_line(strokeWidth=2, color="#9b9a91")
        .encode(
            x=alt.X("annual_volatility:Q", title="Volatilità annualizzata",
                    axis=alt.Axis(format="%")),
            y=alt.Y("annual_return:Q", title="Rendimento annualizzato",
                    axis=alt.Axis(format="%")),
        )
    )
    dots = (
        alt.Chart(points)
        .mark_point(size=140, filled=True)
        .encode(
            x="annual_volatility:Q",
            y="annual_return:Q",
            color=alt.Color(
                "nome:N",
                scale=alt.Scale(domain=list(points["nome"]), range=PALETTE),
                legend=alt.Legend(title=None, orient="top"),
            ),
            tooltip=[
                alt.Tooltip("nome:N", title="Portafoglio"),
                alt.Tooltip("annual_return:Q", title="Rendimento", format=".1%"),
                alt.Tooltip("annual_volatility:Q", title="Volatilità", format=".1%"),
            ],
        )
    )
    labels = (
        alt.Chart(points)
        .mark_text(align="left", dx=10, fontWeight="bold")
        .encode(x="annual_volatility:Q", y="annual_return:Q", text="nome:N")
    )
    return (line + dots + labels).properties(height=380)


def correlation_heatmap(corr: pd.DataFrame) -> alt.Chart:
    """Heatmap della matrice di correlazione con valori nelle celle."""
    heat_df = (
        corr.rename_axis("a").reset_index().melt(id_vars="a", var_name="b", value_name="corr")
    )
    heat = (
        alt.Chart(heat_df)
        .mark_rect()
        .encode(
            x=alt.X("a:N", title=None),
            y=alt.Y("b:N", title=None),
            color=alt.Color(
                "corr:Q",
                scale=alt.Scale(domain=[-1, 0, 1], range=DIVERGING),
                legend=alt.Legend(title="Correlazione"),
            ),
        )
    )
    text = (
        alt.Chart(heat_df)
        .mark_text()
        .encode(
            x="a:N",
            y="b:N",
            text=alt.Text("corr:Q", format=".2f"),
            color=alt.condition(
                "abs(datum.corr) > 0.6", alt.value("white"), alt.value("black")
            ),
        )
    )
    return (heat + text).properties(height=60 * len(corr) + 40)
