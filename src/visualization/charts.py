"""Grafici Altair riusabili per la dashboard."""

import altair as alt
import numpy as np
import pandas as pd

# Palette categorica validata per superficie chiara (dataviz skill, light mode)
PALETTE = ["#2a78d6", "#1baf7a", "#eda100", "#008300", "#4a3aa7", "#e34948", "#e87ba4", "#eb6834"]
# Correlazione: blu = opposti, neutro chiaro = zero, rosso = si muovono insieme
DIVERGING = ["#2a78d6", "#e5e7eb", "#e34948"]
# Rendimenti: convenzione finanza — rosso = perdita, verde = guadagno
LOSS = "#dc2626"
GAIN = "#0ea371"
RETURNS_DIVERGING = [LOSS, "#e5e7eb", GAIN]
TEXT_COLOR = "#1a1d24"
ACCENT = "#b57400"
MUTED = "#9ca3af"


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
    labels = base.mark_text(align="left", dx=6).encode(text=alt.Text("importo:Q", format=",.0f"))
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
    labels = base.mark_text(align="left", dx=6).encode(text=alt.Text("corr:Q", format="+.2f"))
    return (bars + labels).properties(height=26 * len(df) + 20)


def _mds_layout(corr: pd.DataFrame) -> pd.DataFrame:
    """Proietta i titoli in 2D preservando le distanze di correlazione (MDS classico).

    Titoli molto correlati finiscono vicini, titoli indipendenti lontani.
    """
    distances_sq = 2 * (1 - corr.to_numpy())
    n = len(distances_sq)
    centering = np.eye(n) - np.ones((n, n)) / n
    gram = -0.5 * centering @ distances_sq @ centering
    eigenvalues, eigenvectors = np.linalg.eigh(gram)
    order = np.argsort(eigenvalues)[::-1][:2]
    coords = eigenvectors[:, order] * np.sqrt(np.maximum(eigenvalues[order], 0))
    return pd.DataFrame(coords, index=corr.index, columns=["x", "y"])


def galaxy_chart(
    corr: pd.DataFrame, weights: pd.Series, cumulative_returns: pd.Series
) -> alt.Chart:
    """La "galassia" del portafoglio: ogni titolo è un pianeta.

    Dimensione = peso, colore = rendimento nel periodo, distanza = correlazione.
    """
    layout = _mds_layout(corr)
    df = layout.assign(
        ticker=layout.index,
        peso=weights.reindex(layout.index).fillna(0.0),
        rendimento=cumulative_returns.reindex(layout.index),
    ).reset_index(drop=True)

    max_abs = float(df["rendimento"].abs().max()) or 1.0
    dots = (
        alt.Chart(df)
        .mark_circle(opacity=0.9)
        .encode(
            x=alt.X("x:Q", axis=None, scale=alt.Scale(padding=40)),
            y=alt.Y("y:Q", axis=None, scale=alt.Scale(padding=40)),
            size=alt.Size("peso:Q", scale=alt.Scale(range=[400, 4000]), legend=None),
            color=alt.Color(
                "rendimento:Q",
                scale=alt.Scale(domain=[-max_abs, 0, max_abs], range=RETURNS_DIVERGING),
                legend=alt.Legend(title="Rendimento", format="+.0%", orient="bottom"),
            ),
            tooltip=[
                alt.Tooltip("ticker:N", title="Titolo"),
                alt.Tooltip("peso:Q", title="Peso", format=".0%"),
                alt.Tooltip("rendimento:Q", title="Rendimento", format="+.1%"),
            ],
        )
    )
    labels = (
        alt.Chart(df)
        .mark_text(fontWeight="bold", color=TEXT_COLOR, dy=1)
        .encode(x="x:Q", y="y:Q", text="ticker:N")
    )
    return (dots + labels).properties(height=420).configure_view(strokeWidth=0)


def radar_chart(scores: dict[str, float]) -> alt.Chart:
    """Radar a 4 assi dei punteggi di rischio (0 centro, 100 bordo)."""
    names = list(scores)
    n = len(names)
    angles = [np.pi / 2 - 2 * np.pi * i / n for i in range(n)]

    def ring(radius: float) -> pd.DataFrame:
        pts = [
            {"x": radius * np.cos(a), "y": radius * np.sin(a), "ordine": i}
            for i, a in enumerate(angles)
        ]
        return pd.DataFrame(pts + [pts[0] | {"ordine": n}])

    values = pd.DataFrame(
        [
            {
                "x": scores[name] * np.cos(a),
                "y": scores[name] * np.sin(a),
                "ordine": i,
                "asse": name,
                "valore": scores[name],
            }
            for i, (name, a) in enumerate(zip(names, angles, strict=False))
        ]
    )
    closed = pd.concat([values, values.iloc[[0]].assign(ordine=n)])

    grid = alt.layer(
        *[
            alt.Chart(ring(r))
            .mark_line(color="#e0e3e8", strokeWidth=1)
            .encode(x=alt.X("x:Q", axis=None), y=alt.Y("y:Q", axis=None), order="ordine:O")
            for r in (33, 66, 100)
        ]
    )
    area = (
        alt.Chart(closed)
        .mark_area(color=PALETTE[0], opacity=0.35, line={"color": PALETTE[0]})
        .encode(x="x:Q", y="y:Q", order="ordine:O")
    )
    points = (
        alt.Chart(values)
        .mark_point(filled=True, size=90, color=PALETTE[0])
        .encode(
            x="x:Q",
            y="y:Q",
            tooltip=[alt.Tooltip("asse:N"), alt.Tooltip("valore:Q", format=".0f")],
        )
    )
    axis_labels = pd.DataFrame(
        {
            "x": [118 * np.cos(a) for a in angles],
            "y": [118 * np.sin(a) for a in angles],
            "nome": names,
        }
    )
    labels = (
        alt.Chart(axis_labels)
        .mark_text(color=TEXT_COLOR, fontSize=13)
        .encode(x="x:Q", y="y:Q", text="nome:N")
    )
    return (grid + area + points + labels).properties(height=340).configure_view(strokeWidth=0)


def monthly_bars(monthly: pd.Series) -> alt.Chart:
    """Timeline dei rendimenti mensili, colore per segno, etichette dirette."""
    df = pd.DataFrame(
        {
            "mese": monthly.index.strftime("%b %y"),
            "rendimento": monthly.values,
            "ordine": range(len(monthly)),
        }
    )
    base = alt.Chart(df).encode(
        x=alt.X("mese:N", sort=alt.SortField("ordine"), title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("rendimento:Q", title=None, axis=alt.Axis(format="+%")),
    )
    bars = base.mark_bar(cornerRadiusEnd=4, width=28).encode(
        color=alt.condition("datum.rendimento >= 0", alt.value(GAIN), alt.value(LOSS))
    )
    labels = base.mark_text(dy=-10, color=TEXT_COLOR).encode(
        text=alt.Text("rendimento:Q", format="+.1%")
    )
    return (bars + labels).properties(height=240)


def equity_area(values: pd.Series, baseline: float) -> alt.Chart:
    """Curva del capitale: area riempita, verde sopra il capitale investito,
    rossa sotto, con linea tratteggiata sul capitale iniziale."""
    df = values.rename("valore").rename_axis("data").reset_index()
    color = GAIN if float(values.iloc[-1]) >= baseline else LOSS
    low = min(float(values.min()), baseline) * 0.97
    high = max(float(values.max()), baseline) * 1.02
    area = (
        alt.Chart(df)
        .mark_area(opacity=0.14, color=color, line={"color": color, "strokeWidth": 2}, clip=True)
        .encode(
            x=alt.X("data:T", title=None, axis=alt.Axis(grid=False)),
            y=alt.Y(
                "valore:Q",
                title=None,
                scale=alt.Scale(domain=[low, high]),
                axis=alt.Axis(format="~s"),
            ),
            tooltip=[
                alt.Tooltip("data:T", title="Data"),
                alt.Tooltip("valore:Q", title="Valore", format=",.0f"),
            ],
        )
    )
    rule = (
        alt.Chart(pd.DataFrame({"y": [baseline]}))
        .mark_rule(strokeDash=[5, 5], color="#5a6270")
        .encode(y="y:Q")
    )
    return (area + rule).properties(height=190)


def benchmark_overlay(
    pf_value: pd.Series, bench_value: pd.Series, bench_name: str = "QQQ"
) -> alt.Chart:
    """Portafoglio vs benchmark, entrambi a base 100."""
    df = (
        pd.DataFrame(
            {
                "Portafoglio": pf_value / pf_value.iloc[0] * 100,
                bench_name: bench_value / bench_value.iloc[0] * 100,
            }
        )
        .rename_axis("data")
        .reset_index()
        .melt("data", var_name="serie", value_name="valore")
    )
    return (
        alt.Chart(df)
        .mark_line(strokeWidth=2)
        .encode(
            x=alt.X("data:T", title=None, axis=alt.Axis(grid=False)),
            y=alt.Y("valore:Q", title=None, scale=alt.Scale(zero=False)),
            color=alt.Color(
                "serie:N",
                scale=alt.Scale(domain=["Portafoglio", bench_name], range=[ACCENT, MUTED]),
                legend=alt.Legend(title=None, orient="top-left"),
            ),
            tooltip=[
                alt.Tooltip("data:T", title="Data"),
                alt.Tooltip("serie:N", title="Serie"),
                alt.Tooltip("valore:Q", title="Base 100", format=".1f"),
            ],
        )
        .properties(height=280)
    )


def underwater_chart(pf_value: pd.Series) -> alt.Chart:
    """Drawdown nel tempo: quanto sotto il massimo precedente (area rossa)."""
    drawdown = (pf_value / pf_value.cummax() - 1).rename("dd").rename_axis("data")
    df = drawdown.reset_index()
    floor = min(float(drawdown.min()) * 1.15, -0.01)
    return (
        alt.Chart(df)
        .mark_area(color=LOSS, opacity=0.35, line={"color": LOSS, "strokeWidth": 1.5})
        .encode(
            x=alt.X("data:T", title=None, axis=alt.Axis(grid=False)),
            y=alt.Y(
                "dd:Q", title=None, axis=alt.Axis(format="%"), scale=alt.Scale(domain=[floor, 0])
            ),
            tooltip=[
                alt.Tooltip("data:T", title="Data"),
                alt.Tooltip("dd:Q", title="Dal picco", format=".1%"),
            ],
        )
        .properties(height=210)
    )


def simple_line(series: pd.Series, color: str = ACCENT, y_format: str = "%") -> alt.Chart:
    """Linea singola con asse percentuale: per metriche rolling."""
    df = series.rename("valore").rename_axis("data").reset_index()
    return (
        alt.Chart(df)
        .mark_line(strokeWidth=2, color=color)
        .encode(
            x=alt.X("data:T", title=None, axis=alt.Axis(grid=False)),
            y=alt.Y(
                "valore:Q", title=None, axis=alt.Axis(format=y_format), scale=alt.Scale(zero=False)
            ),
            tooltip=[
                alt.Tooltip("data:T", title="Data"),
                alt.Tooltip(
                    "valore:Q", title="Valore", format=".2f" if y_format != "%" else ".1%"
                ),
            ],
        )
        .properties(height=200)
    )


def returns_histogram(daily_returns: pd.Series, var_95: float) -> alt.Chart:
    """Distribuzione dei rendimenti giornalieri con il VaR 95% marcato."""
    df = pd.DataFrame({"ret": daily_returns.dropna()})
    hist = (
        alt.Chart(df)
        .mark_bar(color=PALETTE[0], opacity=0.85)
        .encode(
            x=alt.X("ret:Q", bin=alt.Bin(maxbins=45), title=None, axis=alt.Axis(format="%")),
            y=alt.Y("count()", title=None),
        )
    )
    var_df = pd.DataFrame({"x": [var_95], "label": ["VaR 95%"]})
    rule = (
        alt.Chart(var_df).mark_rule(color=LOSS, strokeWidth=2, strokeDash=[5, 4]).encode(x="x:Q")
    )
    label = (
        alt.Chart(var_df)
        .mark_text(align="right", dx=-6, dy=-88, color=LOSS, fontWeight="bold")
        .encode(x="x:Q", text="label:N")
    )
    return (hist + rule + label).properties(height=210)


def weight_vs_risk_bars(weights: pd.Series, contributions: pd.Series) -> alt.Chart:
    """Peso investito vs contributo al rischio, per titolo (barre appaiate)."""
    order = contributions.sort_values(ascending=False).index
    df = pd.concat(
        [
            weights.reindex(order)
            .rename("valore")
            .rename_axis("ticker")
            .reset_index()
            .assign(tipo="Peso investito"),
            contributions.reindex(order)
            .rename("valore")
            .rename_axis("ticker")
            .reset_index()
            .assign(tipo="Contributo al rischio"),
        ]
    )
    base = alt.Chart(df).encode(
        y=alt.Y("ticker:N", sort=list(order), title=None),
        yOffset=alt.YOffset("tipo:N", sort=["Peso investito", "Contributo al rischio"]),
        x=alt.X("valore:Q", title=None, axis=alt.Axis(format="%")),
    )
    bars = base.mark_bar(height=10, cornerRadiusEnd=3).encode(
        color=alt.Color(
            "tipo:N",
            scale=alt.Scale(
                domain=["Peso investito", "Contributo al rischio"], range=[PALETTE[0], ACCENT]
            ),
            legend=alt.Legend(title=None, orient="top"),
        )
    )
    labels = base.mark_text(align="left", dx=5, fontSize=10, color=TEXT_COLOR).encode(
        text=alt.Text("valore:Q", format=".0%")
    )
    return (bars + labels).properties(height=52 * len(order) + 30)


def contribution_bars(contributions_eur: pd.Series) -> alt.Chart:
    """Contributo in euro di ogni titolo al risultato del portafoglio."""
    order = contributions_eur.sort_values(ascending=False)
    df = order.rename("valore").rename_axis("ticker").reset_index()
    base = alt.Chart(df).encode(
        y=alt.Y("ticker:N", sort=list(order.index), title=None),
        x=alt.X("valore:Q", title=None, axis=alt.Axis(format="~s")),
    )
    bars = base.mark_bar(cornerRadiusEnd=4, height=18).encode(
        color=alt.condition("datum.valore >= 0", alt.value(GAIN), alt.value(LOSS))
    )
    labels = base.mark_text(align="left", dx=6, color=TEXT_COLOR).encode(
        text=alt.Text("valore:Q", format="+,.0f")
    )
    return (bars + labels).properties(height=30 * len(df) + 20)


def efficient_frontier_chart(frontier: pd.DataFrame, points: pd.DataFrame) -> alt.Chart:
    """Frontiera efficiente (linea) + portafogli notevoli (punti etichettati).

    `points` ha colonne: nome, annual_return, annual_volatility.
    """
    line = (
        alt.Chart(frontier)
        .mark_line(strokeWidth=2, color="#9ca3af")
        .encode(
            x=alt.X(
                "annual_volatility:Q", title="Volatilità annualizzata", axis=alt.Axis(format="%")
            ),
            y=alt.Y("annual_return:Q", title="Rendimento annualizzato", axis=alt.Axis(format="%")),
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
            color=alt.value(TEXT_COLOR),
        )
    )
    return (heat + text).properties(height=60 * len(corr) + 40)
