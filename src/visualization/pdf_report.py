"""Report PDF di 3 pagine in stile consulente (reportlab, solo vettoriale).

Pagina 1 — Executive summary: KPI, sintesi, capitale vs benchmark, posizioni.
Pagina 2 — Analisi scientifica: metriche con lettura, drawdown, mesi, health.
Pagina 3 — Diversificazione, stress test, raccomandazioni, metodologia.

Impaginazione coerente col brand dell'app: wordmark, accento blu,
etichette small-caps, footer con disclaimer e numero di pagina.
"""

from datetime import datetime
from io import BytesIO

import pandas as pd
from reportlab.graphics.shapes import Drawing, Line, PolyLine, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    KeepInFrame,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

_ACCENT = colors.HexColor("#1E40AF")
_INK = colors.HexColor("#14171e")
_MUTED = colors.HexColor("#6b7280")
_ROW = colors.HexColor("#f7f8fa")
_GREEN = colors.HexColor("#0e9f6e")
_AMBER = colors.HexColor("#d97706")
_RED = colors.HexColor("#dc2626")
_LINE = colors.HexColor("#e5e7eb")
_ACCENT_SOFT = colors.Color(30 / 255, 64 / 255, 175 / 255, alpha=0.35)
_RED_SOFT = colors.Color(220 / 255, 38 / 255, 38 / 255, alpha=0.16)

_CONTENT_W = 174 * mm  # A4 (210) meno i margini 18+18
_FRAME_H = 254 * mm  # altezza utile per pagina: oltre si restringe, mai pagina 4


def _clean(text: str) -> str:
    """Toglie il markdown (**) e fa l'escape XML per i Paragraph."""
    return (
        text.replace("**", "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )


def _eur(value: float) -> str:
    return f"{value:,.0f} €".replace(",", ".")


def _thin(series: pd.Series, max_points: int = 240) -> pd.Series:
    """Sottocampiona la serie per il grafico (il PDF resta leggero)."""
    valid = series.dropna()
    if len(valid) <= max_points:
        return valid
    step = max(1, len(valid) // max_points)
    thinned = valid.iloc[::step]
    return thinned if thinned.index[-1] == valid.index[-1] else pd.concat([thinned, valid.iloc[[-1]]])


def _date_label(value) -> str:
    try:
        return pd.Timestamp(value).strftime("%d/%m/%Y")
    except (TypeError, ValueError):
        return str(value)


def _footer(canvas, doc) -> None:
    canvas.saveState()
    width, _ = A4
    canvas.setStrokeColor(_LINE)
    canvas.setLineWidth(0.5)
    canvas.line(18 * mm, 14 * mm, width - 18 * mm, 14 * mm)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(_MUTED)
    canvas.drawString(
        18 * mm,
        10 * mm,
        "SmarteeFinance · Portfolio Intelligence · Yahoo Finance data · "
        "not a forecast or financial advice",
    )
    canvas.drawRightString(width - 18 * mm, 10 * mm, f"Page {doc.page} of 3")
    canvas.restoreState()


def _section(title: str) -> Table:
    """Etichetta di sezione con barretta blu, come nell'app."""
    bar = Table(
        [["", title.upper()]],
        colWidths=[1.2 * mm, _CONTENT_W - 1.2 * mm],
        rowHeights=[5 * mm],
    )
    bar.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, 0), _ACCENT),
                ("TEXTCOLOR", (1, 0), (1, 0), _MUTED),
                ("FONTNAME", (1, 0), (1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (1, 0), (1, 0), 8),
                ("LEFTPADDING", (1, 0), (1, 0), 6),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return bar


# ---------------------------------------------------------------- grafici vettoriali


def _axis_labels(low: float, high: float, steps: int = 4) -> list[float]:
    if high <= low:
        high = low + 1
    return [low + (high - low) * i / steps for i in range(steps + 1)]


def _equity_drawing(
    pf_value: pd.Series,
    bench_value: pd.Series | None,
    invested: float,
    benchmark: str,
    width: float = _CONTENT_W,
    height: float = 58 * mm,
) -> Drawing:
    """Capitale nel tempo (€) contro il benchmark, linee vettoriali."""
    drawing = Drawing(width, height)
    pf = _thin(pf_value) * invested
    bench = _thin(bench_value) * invested if bench_value is not None else None

    left, right, bottom, top = 17 * mm, 2 * mm, 6 * mm, 6 * mm
    plot_w, plot_h = width - left - right, height - bottom - top
    lows = [float(pf.min())] + ([float(bench.min())] if bench is not None else [])
    highs = [float(pf.max())] + ([float(bench.max())] if bench is not None else [])
    low, high = min(lows), max(highs)
    pad = (high - low) * 0.06 or high * 0.02 or 1
    low, high = low - pad, high + pad

    def y_at(value: float) -> float:
        return bottom + (value - low) / (high - low) * plot_h

    def points(series: pd.Series) -> list[float]:
        n = len(series)
        coords: list[float] = []
        for i, value in enumerate(series.to_numpy(dtype=float)):
            coords += [left + plot_w * i / max(1, n - 1), y_at(value)]
        return coords

    for level in _axis_labels(low, high):
        y = y_at(level)
        drawing.add(Line(left, y, left + plot_w, y, strokeColor=_LINE, strokeWidth=0.4))
        drawing.add(
            String(left - 2 * mm, y - 1, _eur(level), fontName="Helvetica", fontSize=6.5,
                   fillColor=_MUTED, textAnchor="end")
        )
    # linea del capitale investito (riferimento)
    if low < invested < high:
        drawing.add(
            Line(left, y_at(invested), left + plot_w, y_at(invested),
                 strokeColor=_MUTED, strokeWidth=0.6, strokeDashArray=[1, 2])
        )

    if bench is not None and len(bench) >= 2:
        drawing.add(
            PolyLine(points(bench), strokeColor=_MUTED, strokeWidth=1.0, strokeDashArray=[3, 2])
        )
    if len(pf) >= 2:
        drawing.add(PolyLine(points(pf), strokeColor=_ACCENT, strokeWidth=1.6))

    drawing.add(
        String(left, 1, _date_label(pf.index[0]), fontName="Helvetica", fontSize=6.5,
               fillColor=_MUTED)
    )
    drawing.add(
        String(left + plot_w, 1, _date_label(pf.index[-1]), fontName="Helvetica", fontSize=6.5,
               fillColor=_MUTED, textAnchor="end")
    )
    # legenda in alto a sinistra
    ly = height - 4 * mm
    drawing.add(Rect(left + 2 * mm, ly, 4 * mm, 1.2 * mm, fillColor=_ACCENT, strokeColor=None))
    drawing.add(
        String(left + 7 * mm, ly - 1, "Portfolio", fontName="Helvetica", fontSize=6.5,
               fillColor=_INK)
    )
    if bench is not None:
        drawing.add(
            Rect(left + 24 * mm, ly, 4 * mm, 1.2 * mm, fillColor=_MUTED, strokeColor=None)
        )
        drawing.add(
            String(left + 29 * mm, ly - 1, f"{benchmark} benchmark", fontName="Helvetica",
                   fontSize=6.5, fillColor=_MUTED)
        )
    return drawing


def _underwater_drawing(
    pf_value: pd.Series, width: float = 84 * mm, height: float = 40 * mm
) -> Drawing:
    """Distanza dal massimo precedente (underwater plot), area rossa."""
    drawing = Drawing(width, height)
    valid = _thin(pf_value)
    dd = valid / valid.cummax() - 1

    left, bottom, top = 11 * mm, 5 * mm, 3 * mm
    plot_w, plot_h = width - left - 2 * mm, height - bottom - top
    low = min(float(dd.min()), -0.01) * 1.08

    def y_at(value: float) -> float:
        return bottom + plot_h * (1 - value / low)

    n = len(dd)
    xs = [left + plot_w * i / max(1, n - 1) for i in range(n)]
    top_y = y_at(0)
    poly = [xs[0], top_y]
    for x, value in zip(xs, dd.to_numpy(dtype=float)):
        poly += [x, y_at(value)]
    poly += [xs[-1], top_y]
    drawing.add(Polygon(poly, fillColor=_RED_SOFT, strokeColor=None))
    line_pts: list[float] = []
    for x, value in zip(xs, dd.to_numpy(dtype=float)):
        line_pts += [x, y_at(value)]
    drawing.add(PolyLine(line_pts, strokeColor=_RED, strokeWidth=0.9))
    drawing.add(Line(left, top_y, left + plot_w, top_y, strokeColor=_LINE, strokeWidth=0.5))

    for level in (0.0, low / 2, low):
        drawing.add(
            String(left - 1.5 * mm, y_at(level) - 1, f"{level:.0%}", fontName="Helvetica",
                   fontSize=6, fillColor=_MUTED, textAnchor="end")
        )
    trough = dd.idxmin()
    drawing.add(
        String(left + plot_w, 1, f"trough {dd.min():.1%} on {_date_label(trough)}",
               fontName="Helvetica", fontSize=6, fillColor=_MUTED, textAnchor="end")
    )
    return drawing


def _monthly_drawing(
    monthly: pd.Series, width: float = 84 * mm, height: float = 40 * mm
) -> Drawing:
    """Barre dei rendimenti mensili, verde/rosso secondo il segno."""
    drawing = Drawing(width, height)
    valid = monthly.dropna()
    left, bottom, top = 4 * mm, 6 * mm, 4 * mm
    plot_w, plot_h = width - left - 2 * mm, height - bottom - top
    biggest = max(abs(float(valid.max())), abs(float(valid.min())), 0.01)
    zero_y = bottom + plot_h / 2
    scale = (plot_h / 2 - 1) / biggest

    n = len(valid)
    slot = plot_w / max(1, n)
    bar_w = slot * 0.62
    drawing.add(Line(left, zero_y, left + plot_w, zero_y, strokeColor=_LINE, strokeWidth=0.5))
    for i, (label, value) in enumerate(valid.items()):
        x = left + slot * i + (slot - bar_w) / 2
        h = float(value) * scale
        color = _GREEN if value >= 0 else _RED
        drawing.add(
            Rect(x, zero_y + min(0, h), bar_w, abs(h), fillColor=color, strokeColor=None)
        )
        value_y = zero_y + h + (1.5 * mm if value >= 0 else -3 * mm)
        drawing.add(
            String(x + bar_w / 2, value_y, f"{value:+.0%}", fontName="Helvetica", fontSize=5.5,
                   fillColor=_MUTED, textAnchor="middle")
        )
        month = pd.Timestamp(label).strftime("%b") if not isinstance(label, str) else str(label)
        drawing.add(
            String(x + bar_w / 2, 1, month, fontName="Helvetica", fontSize=5.5,
                   fillColor=_MUTED, textAnchor="middle")
        )
    return drawing


def _weight_risk_drawing(
    weights: pd.Series, contributions: pd.Series, width: float = _CONTENT_W, max_rows: int = 8
) -> Drawing:
    """Peso a confronto col contributo al rischio, coppie di barre orizzontali."""
    top_weights = weights.sort_values(ascending=False).head(max_rows)
    row_h, legend_h = 8 * mm, 6 * mm
    height = row_h * len(top_weights) + legend_h
    drawing = Drawing(width, height)
    left = 14 * mm
    plot_w = width - left - 14 * mm
    biggest = max(float(top_weights.max()), float(contributions.max()) if len(contributions) else 0)

    for i, (ticker, weight) in enumerate(top_weights.items()):
        base_y = height - legend_h - row_h * (i + 1)
        risk = float(contributions.get(ticker, float("nan")))
        drawing.add(
            String(left - 2 * mm, base_y + 2.6 * mm, str(ticker), fontName="Helvetica-Bold",
                   fontSize=7.5, fillColor=_INK, textAnchor="end")
        )
        w_len = plot_w * float(weight) / biggest
        drawing.add(
            Rect(left, base_y + 4 * mm, w_len, 2.4 * mm, fillColor=_ACCENT_SOFT, strokeColor=None)
        )
        drawing.add(
            String(left + w_len + 1.5 * mm, base_y + 4.4 * mm, f"{weight:.1%}",
                   fontName="Helvetica", fontSize=6, fillColor=_MUTED)
        )
        if risk == risk:
            r_len = plot_w * risk / biggest
            drawing.add(
                Rect(left, base_y + 1 * mm, r_len, 2.4 * mm, fillColor=_ACCENT, strokeColor=None)
            )
            drawing.add(
                String(left + r_len + 1.5 * mm, base_y + 1.4 * mm, f"{risk:.1%}",
                       fontName="Helvetica", fontSize=6, fillColor=_MUTED)
            )

    ly = height - 4 * mm
    drawing.add(Rect(left, ly, 4 * mm, 2 * mm, fillColor=_ACCENT_SOFT, strokeColor=None))
    drawing.add(
        String(left + 5 * mm, ly, "capital weight", fontName="Helvetica", fontSize=6.5,
               fillColor=_MUTED)
    )
    drawing.add(Rect(left + 30 * mm, ly, 4 * mm, 2 * mm, fillColor=_ACCENT, strokeColor=None))
    drawing.add(
        String(left + 35 * mm, ly, "share of portfolio risk", fontName="Helvetica",
               fontSize=6.5, fillColor=_MUTED)
    )
    return drawing


def _sector_drawing(
    sector_weights: pd.Series, width: float = 84 * mm, max_rows: int = 7
) -> Drawing:
    """Allocazione per settore, barre orizzontali ordinate per peso."""
    top = sector_weights.sort_values(ascending=False).head(max_rows)
    other = float(sector_weights.sum() - top.sum())
    if other > 0.001:
        top = pd.concat([top, pd.Series({"Other sectors": other})])
    row_h = 7 * mm
    height = row_h * len(top)
    drawing = Drawing(width, height)
    left = 34 * mm
    plot_w = width - left - 12 * mm
    biggest = max(float(top.max()), 0.01)
    for i, (sector, weight) in enumerate(top.items()):
        base_y = height - row_h * (i + 1) + 2 * mm
        drawing.add(
            String(left - 2 * mm, base_y + 0.4 * mm, str(sector)[:24], fontName="Helvetica",
                   fontSize=7, fillColor=_MUTED, textAnchor="end")
        )
        drawing.add(
            Rect(left, base_y, plot_w * float(weight) / biggest, 2.8 * mm,
                 fillColor=_ACCENT if i == 0 else _ACCENT_SOFT, strokeColor=None)
        )
        drawing.add(
            String(left + plot_w * float(weight) / biggest + 1.5 * mm, base_y + 0.4 * mm,
                   f"{weight:.0%}", fontName="Helvetica-Bold", fontSize=6.5, fillColor=_INK)
        )
    return drawing


def _breakdown_drawing(breakdown: dict[str, float], width: float = _CONTENT_W) -> Drawing:
    """Le sei componenti dell'Health Score come barre 0-100."""
    row_h = 6.5 * mm
    height = row_h * len(breakdown)
    drawing = Drawing(width, height)
    left = 42 * mm
    plot_w = width - left - 14 * mm
    for i, (label, score) in enumerate(breakdown.items()):
        base_y = height - row_h * (i + 1) + 1.5 * mm
        color = _GREEN if score >= 67 else _AMBER if score >= 34 else _RED
        drawing.add(
            String(left - 2 * mm, base_y + 0.6 * mm, str(label), fontName="Helvetica",
                   fontSize=7.5, fillColor=_MUTED, textAnchor="end")
        )
        drawing.add(
            Rect(left, base_y, plot_w, 2.6 * mm, fillColor=_ROW, strokeColor=_LINE,
                 strokeWidth=0.3)
        )
        drawing.add(
            Rect(left, base_y, plot_w * min(100, max(0, score)) / 100, 2.6 * mm,
                 fillColor=color, strokeColor=None)
        )
        drawing.add(
            String(left + plot_w + 2 * mm, base_y + 0.4 * mm, f"{score:.0f}",
                   fontName="Helvetica-Bold", fontSize=7.5, fillColor=_INK)
        )
    return drawing


# ---------------------------------------------------------------- report


def build_report(
    portfolio_name: str,
    positions: dict[str, float],
    period: str,
    cum_return: float,
    health_score: int,
    metric_rows: list[tuple],
    insights: list[str],
    suggestions: list[str],
    names: dict[str, str] | None = None,
    *,
    advisor: str | None = None,
    risk_profile: str | None = None,
    benchmark: str = "QQQ",
    currency_note: str = "amounts in EUR, currency effect included",
    executive: str | None = None,
    suitability: dict | None = None,
    annual_return: float | None = None,
    pf_value: pd.Series | None = None,
    bench_value: pd.Series | None = None,
    monthly: pd.Series | None = None,
    contributions: pd.Series | None = None,
    breakdown: dict[str, float] | None = None,
    per_ticker_returns: pd.Series | None = None,
    sector_weights: pd.Series | None = None,
    scenario: dict | None = None,
    coverage_notes: list[str] | None = None,
    risk_free: float | None = None,
) -> bytes:
    """Costruisce il PDF di 3 pagine e lo restituisce come bytes.

    I dati opzionali arricchiscono grafici e sezioni; se mancano, la relativa
    sezione mostra una nota invece di rompere il layout (sempre 3 pagine).
    Le righe di `metric_rows` sono (metrica, portafoglio, lettura) oppure
    (metrica, portafoglio, benchmark, lettura) per il confronto col mercato.
    `scenario` = {"label": str, "direct": float, "total": float} (frazioni).
    `suitability` = {"ok": bool, "text": str} — esito del check di adeguatezza.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=14 * mm,
        bottomMargin=20 * mm,
        title="SmarteeFinance — Portfolio Report",
    )
    styles = getSampleStyleSheet()
    wordmark = ParagraphStyle(
        "wordmark", parent=styles["Normal"], fontSize=9, textColor=_MUTED,
        fontName="Helvetica-Bold",
    )
    h1 = ParagraphStyle(
        "h1", parent=styles["Title"], fontSize=23, alignment=0, textColor=_INK,
        spaceBefore=6, spaceAfter=0, leading=27,
    )
    h2 = ParagraphStyle(
        "h2", parent=styles["Heading2"], fontSize=14, textColor=_INK, spaceBefore=2,
        spaceAfter=2, fontName="Helvetica-Bold",
    )
    subtitle = ParagraphStyle(
        "sub", parent=styles["Normal"], fontSize=9.5, textColor=_MUTED, spaceAfter=10, leading=13
    )
    body = ParagraphStyle("body", parent=styles["Normal"], fontSize=9.5, leading=14,
                          textColor=_INK)
    small = ParagraphStyle("small", parent=styles["Normal"], fontSize=8, leading=11.5,
                           textColor=_MUTED)
    reading = ParagraphStyle("reading", parent=styles["Normal"], fontSize=8, leading=10.5,
                             textColor=_MUTED)
    caption = ParagraphStyle("caption", parent=styles["Normal"], fontSize=7.5, leading=10,
                             textColor=_MUTED, spaceBefore=2)

    total = sum(positions.values())
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    names = names or {}
    weights = pd.Series(positions, dtype=float) / total if total else pd.Series(dtype=float)
    health_color = _GREEN if health_score >= 67 else _AMBER if health_score >= 34 else _RED
    return_color = _GREEN if cum_return >= 0 else _RED

    def page_header(topic: str) -> list:
        return [
            Paragraph("SMARTEEFINANCE · PORTFOLIO INTELLIGENCE", wordmark),
            HRFlowable(width="100%", thickness=1, color=_ACCENT, spaceAfter=6),
            Paragraph(topic, h2),
            Paragraph(f"{portfolio_name} · {now}", subtitle),
        ]

    def bullets(items: list[str], cap: int) -> list:
        flow = []
        for item in items[:cap]:
            flow.append(Paragraph(f"–&nbsp;&nbsp;{_clean(item)}", body))
            flow.append(Spacer(1, 3))
        if not items:
            flow.append(Paragraph("Nothing flagged by the monitored rules.", small))
        return flow

    # ------------------------------------------------------------ pagina 1
    meta_bits = [portfolio_name]
    if advisor:
        meta_bits.append(f"prepared by {advisor}")
    if risk_profile and risk_profile != "Not set":
        meta_bits.append(f"{risk_profile.lower()} profile")
    if pf_value is not None and len(pf_value.dropna()) >= 2:
        window = pf_value.dropna().index
        meta_bits.append(
            f"observation window {_date_label(window[0])} – {_date_label(window[-1])}"
        )
    meta_bits += [f"generated on {now}", currency_note]

    page1: list = [
        Paragraph("SMARTEEFINANCE · PORTFOLIO INTELLIGENCE", wordmark),
        HRFlowable(width="100%", thickness=2, color=_ACCENT, spaceAfter=10),
        Paragraph("Portfolio Report", h1),
        Paragraph(" · ".join(meta_bits), subtitle),
    ]

    kpi_labels = ["HEALTH SCORE", "ESTIMATED VALUE", f"RETURN ({period.upper()})", "CAGR",
                  "INVESTED"]
    kpi_values = [
        f"{health_score}/100",
        _eur(total * (1 + cum_return)),
        f"{cum_return:+.1%}",
        f"{annual_return:+.1%}" if annual_return is not None else "—",
        _eur(total),
    ]
    kpi = Table([kpi_labels, kpi_values], colWidths=[_CONTENT_W / 5] * 5)
    kpi.setStyle(
        TableStyle(
            [
                ("TEXTCOLOR", (0, 0), (-1, 0), _MUTED),
                ("FONTSIZE", (0, 0), (-1, 0), 6.5),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 1), (-1, 1), 13.5),
                ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
                ("TEXTCOLOR", (0, 1), (-1, 1), _INK),
                ("TEXTCOLOR", (0, 1), (0, 1), health_color),
                ("TEXTCOLOR", (2, 1), (2, 1), return_color),
                ("TOPPADDING", (0, 1), (-1, 1), 5),
                ("BOTTOMPADDING", (0, 1), (-1, 1), 8),
                ("LINEBELOW", (0, 1), (-1, 1), 0.5, _LINE),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    page1 += [kpi, Spacer(1, 10)]

    page1 += [_section("Executive summary"), Spacer(1, 5)]
    if executive:
        page1.append(Paragraph(_clean(executive), body))
    else:
        page1.append(Paragraph("Summary not available for this analysis.", small))
    if suitability:
        ok = bool(suitability.get("ok"))
        box = Table(
            [["", Paragraph(
                f"<b>Suitability check — {'within' if ok else 'OUTSIDE'} the declared "
                f"profile.</b> {_clean(suitability.get('text', ''))}", body)]],
            colWidths=[1.2 * mm, _CONTENT_W - 1.2 * mm],
        )
        box.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, 0), _GREEN if ok else _RED),
                    ("BACKGROUND", (1, 0), (1, 0), _ROW),
                    ("TOPPADDING", (1, 0), (1, 0), 4),
                    ("BOTTOMPADDING", (1, 0), (1, 0), 4),
                    ("LEFTPADDING", (1, 0), (1, 0), 6),
                ]
            )
        )
        page1 += [Spacer(1, 5), box]
    page1.append(Spacer(1, 10))

    page1 += [_section(f"Capital over time ({period}) vs {benchmark}"), Spacer(1, 5)]
    if pf_value is not None and len(pf_value.dropna()) >= 2:
        page1.append(_equity_drawing(pf_value, bench_value, total, benchmark))
        page1.append(
            Paragraph(
                "Dotted line = capital invested today, projected backwards. "
                f"Benchmark: {benchmark} rebased to the same starting capital.",
                caption,
            )
        )
    else:
        page1.append(Paragraph("Price history not available.", small))
    page1.append(Spacer(1, 10))

    page1 += [_section("Holdings"), Spacer(1, 5)]
    sorted_pos = sorted(positions.items(), key=lambda kv: -kv[1])
    shown, rest = sorted_pos[:12], sorted_pos[12:]
    rows = [["Ticker", "Company", "Amount", "Weight", f"Return ({period})", "Risk share"]]
    for ticker, amount in shown:
        ret = per_ticker_returns.get(ticker) if per_ticker_returns is not None else None
        risk = contributions.get(ticker) if contributions is not None else None
        rows.append(
            [
                ticker,
                names.get(ticker, "")[:34],
                _eur(amount),
                f"{amount / total:.1%}",
                f"{ret:+.1%}" if ret is not None and ret == ret else "—",
                f"{risk:.1%}" if risk is not None and risk == risk else "—",
            ]
        )
    if rest:
        rest_total = sum(amount for _, amount in rest)
        rows.append(
            [f"+{len(rest)}", "other holdings", _eur(rest_total),
             f"{rest_total / total:.1%}", "", ""]
        )
    composition = Table(rows, colWidths=[18 * mm, 62 * mm, 28 * mm, 18 * mm, 26 * mm, 22 * mm])
    composition.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 7.5),
                ("TEXTCOLOR", (0, 0), (-1, 0), _MUTED),
                ("FONTSIZE", (0, 1), (-1, -1), 9),
                ("TEXTCOLOR", (0, 1), (-1, -1), _INK),
                ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
                ("TEXTCOLOR", (1, 1), (1, -1), _MUTED),
                ("LINEBELOW", (0, 0), (-1, 0), 0.75, _ACCENT),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _ROW]),
                ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
                ("TOPPADDING", (0, 0), (-1, -1), 3.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
            ]
        )
    )
    page1.append(composition)
    if coverage_notes:
        page1.append(
            Paragraph(
                "Data coverage: " + " · ".join(_clean(note) for note in coverage_notes),
                caption,
            )
        )

    # ------------------------------------------------------------ pagina 2
    page2: list = page_header("Risk & performance analytics")

    page2 += [_section(f"Metrics, portfolio vs {benchmark}, and how to read them"), Spacer(1, 5)]
    metric_table_rows = [["Metric", "Portfolio", benchmark, "Reading"]]
    for row in metric_rows:
        if len(row) == 4:
            name, value, bench_cell, interpretation = row
        else:
            name, value, interpretation = row
            bench_cell = "—"
        metric_table_rows.append(
            [name, value, bench_cell, Paragraph(_clean(interpretation), reading)]
        )
    metrics_table = Table(metric_table_rows, colWidths=[40 * mm, 23 * mm, 23 * mm, 88 * mm])
    metrics_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 7.5),
                ("TEXTCOLOR", (0, 0), (-1, 0), _MUTED),
                ("LINEBELOW", (0, 0), (-1, 0), 0.75, _ACCENT),
                ("FONTSIZE", (0, 1), (2, -1), 9),
                ("TEXTCOLOR", (0, 1), (0, -1), _MUTED),
                ("FONTNAME", (1, 1), (1, -1), "Helvetica-Bold"),
                ("TEXTCOLOR", (1, 1), (1, -1), _INK),
                ("TEXTCOLOR", (2, 1), (2, -1), _MUTED),
                ("ALIGN", (1, 0), (2, -1), "RIGHT"),
                ("VALIGN", (0, 1), (-1, -1), "MIDDLE"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _ROW]),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    page2 += [metrics_table, Spacer(1, 12)]

    half_w = (_CONTENT_W - 6 * mm) / 2
    chart_cells: list = []
    if pf_value is not None and len(pf_value.dropna()) >= 2:
        chart_cells.append(
            [
                _section_mini("Distance from the peak (underwater)"),
                _underwater_drawing(pf_value, width=half_w),
            ]
        )
    if monthly is not None and len(monthly.dropna()) >= 2:
        chart_cells.append(
            [
                _section_mini("Monthly returns (last 12 months)"),
                _monthly_drawing(monthly, width=half_w),
            ]
        )
    if chart_cells:
        while len(chart_cells) < 2:
            chart_cells.append(["", Spacer(1, 1)])
        charts_row = Table(
            [[cell[0] for cell in chart_cells], [cell[1] for cell in chart_cells]],
            colWidths=[half_w + 3 * mm] * 2,
        )
        charts_row.setStyle(
            TableStyle(
                [
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        page2 += [charts_row, Spacer(1, 12)]

    page2 += [_section("Health Score: the six components"), Spacer(1, 5)]
    if breakdown:
        page2.append(_breakdown_drawing(breakdown))
        page2.append(
            Paragraph(
                "0-100 per component; the Health Score is their average. "
                "Green ≥ 67, amber 34-66, red ≤ 33.",
                caption,
            )
        )
    else:
        page2.append(Paragraph("Component breakdown not available.", small))

    # ------------------------------------------------------------ pagina 3
    page3: list = page_header("Diversification, scenarios & recommendations")

    half_w3 = (_CONTENT_W - 6 * mm) / 2
    div_cells: list = []
    if contributions is not None and len(contributions) and len(weights):
        div_cells.append(
            [
                _section_mini("Weight vs risk contribution"),
                _weight_risk_drawing(weights, contributions, width=half_w3, max_rows=6),
                Paragraph(
                    "Risk share = contribution to portfolio variance (covariances "
                    "included). A holding whose risk share far exceeds its weight "
                    "dominates the swings.",
                    caption,
                ),
            ]
        )
    if sector_weights is not None and len(sector_weights):
        div_cells.append(
            [
                _section_mini("Allocation by sector"),
                _sector_drawing(sector_weights, width=half_w3),
                Paragraph(
                    "Sectors from Yahoo Finance company profiles, weighted by capital.",
                    caption,
                ),
            ]
        )
    if div_cells:
        while len(div_cells) < 2:
            div_cells.append(["", Spacer(1, 1), ""])
        div_row = Table(
            [
                [cell[0] for cell in div_cells],
                [cell[1] for cell in div_cells],
                [cell[2] for cell in div_cells],
            ],
            colWidths=[half_w3 + 3 * mm] * 2,
        )
        div_row.setStyle(
            TableStyle(
                [
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        page3.append(div_row)
    else:
        page3.append(Paragraph("Risk decomposition not available.", small))
    page3.append(Spacer(1, 8))

    hhi = float((weights**2).sum()) if len(weights) else float("nan")
    eff_n = 1 / hhi if hhi and hhi == hhi else float("nan")
    conc = Table(
        [
            ["HOLDINGS", "EFFECTIVE HOLDINGS", "TOP POSITION", "CONCENTRATION (HHI)"],
            [
                f"{len(weights)}",
                f"{eff_n:.1f}" if eff_n == eff_n else "—",
                f"{float(weights.max()):.0%}" if len(weights) else "—",
                f"{hhi:.2f}" if hhi == hhi else "—",
            ],
        ],
        colWidths=[_CONTENT_W / 4] * 4,
    )
    conc.setStyle(
        TableStyle(
            [
                ("TEXTCOLOR", (0, 0), (-1, 0), _MUTED),
                ("FONTSIZE", (0, 0), (-1, 0), 6.5),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 1), (-1, 1), 12),
                ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
                ("TEXTCOLOR", (0, 1), (-1, 1), _INK),
                ("TOPPADDING", (0, 1), (-1, 1), 4),
                ("BOTTOMPADDING", (0, 1), (-1, 1), 6),
                ("LINEBELOW", (0, 1), (-1, 1), 0.5, _LINE),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    page3 += [
        conc,
        Paragraph(
            "Effective holdings = 1/HHI: how many equally-weighted positions your "
            "concentration is equivalent to.",
            caption,
        ),
        Spacer(1, 8),
    ]

    page3 += [_section("Stress scenario on your data"), Spacer(1, 5)]
    if scenario:
        page3.append(
            Paragraph(
                f"If <b>{_clean(scenario['label'])}</b>, the direct hit on the portfolio "
                f"is <b>{scenario['direct']:+.1%}</b> ({_eur(total * scenario['direct'])}); "
                f"including the historical co-movement of the other holdings, the estimated "
                f"total impact is <b>{scenario['total']:+.1%}</b> "
                f"({_eur(total * scenario['total'])}).",
                body,
            )
        )
        page3.append(
            Paragraph(
                "Contagion estimated from each holding's historical beta to the shocked "
                "position over the selected period. An estimate, not a forecast.",
                caption,
            )
        )
    else:
        page3.append(Paragraph("No stress scenario computed for this portfolio.", small))
    page3.append(Spacer(1, 8))

    page3 += [_section("Points of attention"), Spacer(1, 5)]
    page3 += bullets(insights, cap=4)
    page3.append(Spacer(1, 6))

    page3 += [_section("Recommendations"), Spacer(1, 5)]
    page3 += bullets(suggestions, cap=4)
    page3.append(Spacer(1, 8))

    method_bits = [
        "Prices: Yahoo Finance daily closes over the selected period"
        + (f" ({period})" if period else "") + ", converted to EUR where noted.",
        "Returns: geometric (CAGR) — never arithmetic-mean annualization, which "
        "overstates results under volatility.",
        f"Sharpe/Sortino: excess return over the risk-free rate"
        + (f" ({risk_free:.2%}, 3-month US T-bill ^IRX)" if risk_free is not None else "")
        + "; Sortino penalizes downside deviation only.",
        "VaR 95%: historical 5th percentile of daily returns — no normality assumed; "
        "expected shortfall = average of the tail beyond it.",
        f"Beta/alpha: OLS regression of daily portfolio returns on {benchmark}.",
        "Risk contributions: share of portfolio variance per holding, covariances included.",
        "All figures are computed from the observed period and are estimates, "
        "not forecasts. This document is not financial advice.",
    ]
    if pf_value is not None and 2 <= len(pf_value.dropna()) < 200:
        method_bits.insert(
            0,
            "CAUTION: the observation window is shorter than one year — annualized "
            "figures (CAGR, volatility, Sharpe/Sortino) extrapolate from few months "
            "and should be read as indicative only.",
        )
    page3 += [_section("Methodology & assumptions"), Spacer(1, 5)]
    for bit in method_bits:
        page3.append(Paragraph(f"–&nbsp;&nbsp;{_clean(bit)}", small))
        page3.append(Spacer(1, 1.5))

    story = [
        KeepInFrame(_CONTENT_W, _FRAME_H, page1, mode="shrink"),
        PageBreak(),
        KeepInFrame(_CONTENT_W, _FRAME_H, page2, mode="shrink"),
        PageBreak(),
        KeepInFrame(_CONTENT_W, _FRAME_H, page3, mode="shrink"),
    ]
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()


def _section_mini(title: str) -> Table:
    """Variante stretta dell'etichetta di sezione per le mezze colonne."""
    bar = Table(
        [["", title.upper()]],
        colWidths=[1.2 * mm, 80 * mm],
        rowHeights=[5 * mm],
    )
    bar.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, 0), _ACCENT),
                ("TEXTCOLOR", (1, 0), (1, 0), _MUTED),
                ("FONTNAME", (1, 0), (1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (1, 0), (1, 0), 7),
                ("LEFTPADDING", (1, 0), (1, 0), 6),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return bar
