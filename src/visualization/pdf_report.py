"""Report PDF di 3 pagine in stile consulente (reportlab, solo vettoriale).

Pagina 1 — Executive summary: KPI, sintesi, capitale vs benchmark, posizioni.
Pagina 2 — Analisi scientifica: metriche con lettura, drawdown, mesi, health.
Pagina 3 — Diversificazione, stress test, raccomandazioni, metodologia.

Impaginazione coerente col brand dell'app: wordmark, accento blu,
etichette small-caps, footer con disclaimer e numero di pagina.
"""

import hashlib
from datetime import datetime
from io import BytesIO

import pandas as pd

from src.i18n import t_in
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


def _footer(canvas, doc, report_id: str, lang: str = "en") -> None:
    """Footer legale su ogni pagina: fonte, ID documento, avvertenze obbligatorie."""
    canvas.saveState()
    width, _ = A4
    canvas.setStrokeColor(_LINE)
    canvas.setLineWidth(0.5)
    canvas.line(18 * mm, 14.5 * mm, width - 18 * mm, 14.5 * mm)
    canvas.setFont("Helvetica", 6.5)
    canvas.setFillColor(_MUTED)
    canvas.drawString(18 * mm, 11 * mm, t_in(lang, "pdf.footer_line1", rid=report_id))
    canvas.drawString(18 * mm, 7.5 * mm, t_in(lang, "pdf.footer_line2"))
    canvas.drawRightString(width - 18 * mm, 11 * mm, t_in(lang, "pdf.page", n=doc.page))
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
    label_portfolio: str = "Portfolio",
    label_benchmark: str | None = None,
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
        String(left + 7 * mm, ly - 1, label_portfolio, fontName="Helvetica", fontSize=6.5,
               fillColor=_INK)
    )
    if bench is not None:
        drawing.add(
            Rect(left + 24 * mm, ly, 4 * mm, 1.2 * mm, fillColor=_MUTED, strokeColor=None)
        )
        drawing.add(
            String(left + 29 * mm, ly - 1, label_benchmark or f"{benchmark} benchmark",
                   fontName="Helvetica", fontSize=6.5, fillColor=_MUTED)
        )
    return drawing


def _underwater_drawing(
    pf_value: pd.Series,
    width: float = 84 * mm,
    height: float = 40 * mm,
    trough_label: str | None = None,
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
    text = trough_label or f"trough {dd.min():.1%} on {_date_label(trough)}"
    drawing.add(
        String(left + plot_w, 1, text,
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
    weights: pd.Series,
    contributions: pd.Series,
    width: float = _CONTENT_W,
    max_rows: int = 8,
    legend_weight: str = "capital weight",
    legend_risk: str = "share of portfolio risk",
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
        String(left + 5 * mm, ly, legend_weight, fontName="Helvetica", fontSize=6.5,
               fillColor=_MUTED)
    )
    drawing.add(Rect(left + 30 * mm, ly, 4 * mm, 2 * mm, fillColor=_ACCENT, strokeColor=None))
    drawing.add(
        String(left + 35 * mm, ly, legend_risk, fontName="Helvetica",
               fontSize=6.5, fillColor=_MUTED)
    )
    return drawing


def _sector_drawing(
    sector_weights: pd.Series,
    width: float = 84 * mm,
    max_rows: int = 7,
    other_label: str = "Other sectors",
) -> Drawing:
    """Allocazione per settore, barre orizzontali ordinate per peso."""
    top = sector_weights.sort_values(ascending=False).head(max_rows)
    other = float(sector_weights.sum() - top.sum())
    if other > 0.001:
        top = pd.concat([top, pd.Series({other_label: other})])
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
    currency_note: str | None = None,
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
    invested: float | None = None,
    pnl: float | None = None,
    pnl_pct: float | None = None,
    per_ticker_pnl: pd.Series | None = None,
    lang: str = "en",
) -> bytes:
    """Costruisce il PDF di 3 pagine e lo restituisce come bytes.

    I dati opzionali arricchiscono grafici e sezioni; se mancano, la relativa
    sezione mostra una nota invece di rompere il layout (sempre 3 pagine).
    Le righe di `metric_rows` sono (metrica, portafoglio, lettura) oppure
    (metrica, portafoglio, benchmark, lettura) per il confronto col mercato.
    `scenario` = {"label": str, "direct": float, "total": float} (frazioni).
    `suitability` = {"ok": bool, "text": str} — esito del check di adeguatezza.
    """
    def T(key: str, **kwargs) -> str:
        return t_in(lang, key, **kwargs)

    def comp_name(name: str) -> str:
        translated = t_in(lang, f"comp.{name}")
        return name if translated.startswith("comp.") else translated

    if currency_note is None:
        currency_note = T("pdf.currency_eur")

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=14 * mm,
        bottomMargin=20 * mm,
        title=T("pdf.doc_title"),
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
    # identificativo documento per riferimento e tracciabilità nelle revisioni
    report_id = hashlib.sha1(
        f"{portfolio_name}|{advisor or ''}|{now}".encode()
    ).hexdigest()[:8].upper()
    names = names or {}
    weights = pd.Series(positions, dtype=float) / total if total else pd.Series(dtype=float)
    health_color = _GREEN if health_score >= 67 else _AMBER if health_score >= 34 else _RED
    return_color = _GREEN if cum_return >= 0 else _RED

    def page_header(topic: str) -> list:
        return [
            Paragraph("SMARTEEFINANCE · PORTFOLIO INTELLIGENCE", wordmark),
            HRFlowable(width="100%", thickness=1, color=_ACCENT, spaceAfter=6),
            Paragraph(topic, h2),
            Paragraph(_clean(f"{portfolio_name} · {now}"), subtitle),
        ]

    def bullets(items: list[str], cap: int) -> list:
        flow = []
        for item in items[:cap]:
            flow.append(Paragraph(f"–&nbsp;&nbsp;{_clean(item)}", body))
            flow.append(Spacer(1, 3))
        if not items:
            flow.append(Paragraph(T("pdf.none_flagged"), small))
        return flow

    # ------------------------------------------------------------ pagina 1
    meta_bits = [portfolio_name]
    if advisor:
        meta_bits.append(T("pdf.prepared_by", advisor=advisor))
    if risk_profile and risk_profile != "Not set":
        profile_label = t_in(lang, f"prof.{risk_profile}")
        if profile_label.startswith("prof."):
            profile_label = risk_profile
        meta_bits.append(T("pdf.profile", profile=profile_label.lower()))
    if pf_value is not None and len(pf_value.dropna()) >= 2:
        window = pf_value.dropna().index
        meta_bits.append(
            T("pdf.window", start=_date_label(window[0]), end=_date_label(window[-1]))
        )
    meta_bits += [T("pdf.generated", now=now), f"Ref. {report_id}", currency_note]

    page1: list = [
        Paragraph("SMARTEEFINANCE · PORTFOLIO INTELLIGENCE", wordmark),
        HRFlowable(width="100%", thickness=2, color=_ACCENT, spaceAfter=10),
        Paragraph(T("pdf.title"), h1),
        Paragraph(_clean(" · ".join(meta_bits)), subtitle),
    ]

    has_pnl = pnl is not None and pnl == pnl
    gain_color = _GREEN if has_pnl and pnl >= 0 else _RED
    gain_value = "—"
    gain_label = T("pdf.kpi_gain")
    if has_pnl:
        gain_value = ("+" if pnl >= 0 else "") + _eur(pnl)
        if pnl_pct is not None and pnl_pct == pnl_pct:
            gain_label += f" ({pnl_pct:+.1%})"
    kpi_labels = [
        T("pdf.kpi_health"),
        T("pdf.kpi_value"),
        gain_label,
        T("pdf.kpi_return", period=period.upper()),
        T("pdf.kpi_cagr"),
        T("pdf.kpi_invested"),
    ]
    kpi_values = [
        f"{health_score}/100",
        _eur(total),
        gain_value,
        f"{cum_return:+.1%}",
        f"{annual_return:+.1%}" if annual_return is not None else "—",
        _eur(invested) if invested is not None else _eur(total),
    ]
    kpi = Table([kpi_labels, kpi_values], colWidths=[_CONTENT_W / 6] * 6)
    kpi.setStyle(
        TableStyle(
            [
                ("TEXTCOLOR", (0, 0), (-1, 0), _MUTED),
                ("FONTSIZE", (0, 0), (-1, 0), 6),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 1), (-1, 1), 11.5),
                ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
                ("TEXTCOLOR", (0, 1), (-1, 1), _INK),
                ("TEXTCOLOR", (0, 1), (0, 1), health_color),
                ("TEXTCOLOR", (2, 1), (2, 1), gain_color),
                ("TEXTCOLOR", (3, 1), (3, 1), return_color),
                ("TOPPADDING", (0, 1), (-1, 1), 5),
                ("BOTTOMPADDING", (0, 1), (-1, 1), 8),
                ("LINEBELOW", (0, 1), (-1, 1), 0.5, _LINE),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    page1 += [kpi, Spacer(1, 10)]

    page1 += [_section(T("pdf.exec_summary")), Spacer(1, 5)]
    if executive:
        page1.append(Paragraph(_clean(executive), body))
    else:
        page1.append(Paragraph(T("pdf.no_summary"), small))
    if suitability:
        ok = bool(suitability.get("ok"))
        box = Table(
            [["", Paragraph(
                T(
                    "pdf.check_text",
                    status=T("pdf.within") if ok else T("pdf.outside"),
                    text=_clean(suitability.get("text", "")),
                )
                + f"<font size=7 color='#6b7280'>{T('pdf.check_caveat')}</font>", body)]],
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

    page1 += [_section(T("pdf.capital_section", period=period, benchmark=benchmark)),
              Spacer(1, 5)]
    if pf_value is not None and len(pf_value.dropna()) >= 2:
        page1.append(
            _equity_drawing(
                pf_value,
                bench_value,
                total,
                benchmark,
                label_portfolio=T("pdf.portfolio_legend"),
                label_benchmark=T("pdf.benchmark_legend", benchmark=benchmark),
            )
        )
        page1.append(Paragraph(T("pdf.capital_caption", benchmark=benchmark), caption))
    else:
        page1.append(Paragraph(T("pdf.no_history"), small))
    page1.append(Spacer(1, 10))

    page1 += [_section(T("pdf.holdings")), Spacer(1, 5)]
    sorted_pos = sorted(positions.items(), key=lambda kv: -kv[1])
    shown, rest = sorted_pos[:12], sorted_pos[12:]
    rows = [[
        T("pdf.h_ticker"), T("pdf.h_company"), T("pdf.h_value"), T("pdf.h_pnl"),
        T("pdf.h_weight"), T("pdf.h_return", period=period), T("pdf.h_risk"),
    ]]
    for ticker, amount in shown:
        ret = per_ticker_returns.get(ticker) if per_ticker_returns is not None else None
        risk = contributions.get(ticker) if contributions is not None else None
        row_pnl = per_ticker_pnl.get(ticker) if per_ticker_pnl is not None else None
        pnl_cell = "—"
        if row_pnl is not None and row_pnl == row_pnl:
            pnl_cell = ("+" if row_pnl >= 0 else "") + _eur(row_pnl)
        rows.append(
            [
                ticker,
                names.get(ticker, "")[:26],
                _eur(amount),
                pnl_cell,
                f"{amount / total:.1%}",
                f"{ret:+.1%}" if ret is not None and ret == ret else "—",
                f"{risk:.1%}" if risk is not None and risk == risk else "—",
            ]
        )
    if rest:
        rest_total = sum(amount for _, amount in rest)
        rows.append(
            [f"+{len(rest)}", T("pdf.other_holdings"), _eur(rest_total), "",
             f"{rest_total / total:.1%}", "", ""]
        )
    composition = Table(
        rows, colWidths=[16 * mm, 48 * mm, 25 * mm, 23 * mm, 16 * mm, 24 * mm, 22 * mm]
    )
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
                T("pdf.coverage") + " · ".join(_clean(note) for note in coverage_notes),
                caption,
            )
        )

    # ------------------------------------------------------------ pagina 2
    page2: list = page_header(T("pdf.p2_title"))

    page2 += [_section(T("pdf.metrics_section", benchmark=benchmark)), Spacer(1, 5)]
    metric_table_rows = [[T("pdf.h_metric"), T("pdf.h_portfolio"), benchmark, T("pdf.h_reading")]]
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
                _section_mini(T("pdf.underwater_title")),
                _underwater_drawing(
                    pf_value,
                    width=half_w,
                    trough_label=T(
                        "pdf.trough",
                        dd=f"{(pf_value.dropna() / pf_value.dropna().cummax() - 1).min():.1%}",
                        date=_date_label(
                            (pf_value.dropna() / pf_value.dropna().cummax() - 1).idxmin()
                        ),
                    ),
                ),
            ]
        )
    if monthly is not None and len(monthly.dropna()) >= 2:
        chart_cells.append(
            [
                _section_mini(T("pdf.monthly_title")),
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

    page2 += [_section(T("pdf.breakdown_section")), Spacer(1, 5)]
    if breakdown:
        page2.append(_breakdown_drawing({comp_name(k): v for k, v in breakdown.items()}))
        page2.append(Paragraph(T("pdf.breakdown_caption"), caption))
    else:
        page2.append(Paragraph(T("pdf.no_breakdown"), small))

    # ------------------------------------------------------------ pagina 3
    page3: list = page_header(T("pdf.p3_title"))

    half_w3 = (_CONTENT_W - 6 * mm) / 2
    div_cells: list = []
    if contributions is not None and len(contributions) and len(weights):
        div_cells.append(
            [
                _section_mini(T("pdf.wr_title")),
                _weight_risk_drawing(
                    weights,
                    contributions,
                    width=half_w3,
                    max_rows=6,
                    legend_weight=T("pdf.legend_weight"),
                    legend_risk=T("pdf.legend_risk"),
                ),
                Paragraph(T("pdf.wr_caption"), caption),
            ]
        )
    if sector_weights is not None and len(sector_weights):
        div_cells.append(
            [
                _section_mini(T("pdf.sector_title")),
                _sector_drawing(sector_weights, width=half_w3,
                                other_label=T("pdf.other_sectors")),
                Paragraph(T("pdf.sector_caption"), caption),
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
        page3.append(Paragraph(T("pdf.no_risk_decomp"), small))
    page3.append(Spacer(1, 8))

    hhi = float((weights**2).sum()) if len(weights) else float("nan")
    eff_n = 1 / hhi if hhi and hhi == hhi else float("nan")
    conc = Table(
        [
            [T("pdf.c_holdings"), T("pdf.c_effective"), T("pdf.c_top"), T("pdf.c_hhi")],
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
        Paragraph(T("pdf.conc_caption"), caption),
        Spacer(1, 8),
    ]

    page3 += [_section(T("pdf.stress_title")), Spacer(1, 5)]
    if scenario:
        page3.append(
            Paragraph(
                T(
                    "pdf.stress_text",
                    label=_clean(scenario["label"]),
                    direct=f"{scenario['direct']:+.1%}",
                    direct_eur=_eur(total * scenario["direct"]),
                    total=f"{scenario['total']:+.1%}",
                    total_eur=_eur(total * scenario["total"]),
                ),
                body,
            )
        )
        page3.append(Paragraph(T("pdf.stress_caption"), caption))
    else:
        page3.append(Paragraph(T("pdf.no_scenario"), small))
    page3.append(Spacer(1, 8))

    page3 += [_section(T("pdf.attention_title")), Spacer(1, 5)]
    page3 += bullets(insights, cap=3)
    page3.append(Spacer(1, 6))

    page3 += [_section(T("pdf.obs_title")), Spacer(1, 5)]
    page3 += bullets(suggestions, cap=3)
    page3.append(Paragraph(T("pdf.obs_caption"), caption))
    page3.append(Spacer(1, 8))

    fine = ParagraphStyle(
        "fine", parent=styles["Normal"], fontSize=6.2, leading=8.2, textColor=_MUTED,
        spaceAfter=3,
    )
    rf_note = T("pdf.notice_rf", rate=f"{risk_free:.2%}") if risk_free is not None else ""
    notice_bits = [
        T("pdf.notice_data", period=period),
        *([T("pdf.notice_pnl")] if has_pnl else []),
        T("pdf.notice_costs"),
        T("pdf.notice_returns", rf=rf_note),
        T("pdf.notice_var", benchmark=benchmark),
        T("pdf.notice_estimates"),
        T("pdf.notice_no_advice"),
        T("pdf.notice_profile"),
        T("pdf.notice_confidential"),
    ]
    if pf_value is not None and 2 <= len(pf_value.dropna()) < 200:
        notice_bits.insert(0, T("pdf.notice_caution"))
    page3 += [_section(T("pdf.notices_title")), Spacer(1, 5)]
    half = (len(notice_bits) + 1) // 2
    notice_cols = Table(
        [
            [
                [Paragraph(_clean(bit), fine) for bit in notice_bits[:half]],
                [Paragraph(_clean(bit), fine) for bit in notice_bits[half:]],
            ]
        ],
        colWidths=[_CONTENT_W / 2] * 2,
    )
    notice_cols.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (0, 0), 0),
                ("LEFTPADDING", (1, 0), (1, 0), 4),
                ("RIGHTPADDING", (0, 0), (0, 0), 4),
                ("RIGHTPADDING", (1, 0), (1, 0), 0),
            ]
        )
    )
    page3.append(notice_cols)

    story = [
        KeepInFrame(_CONTENT_W, _FRAME_H, page1, mode="shrink"),
        PageBreak(),
        KeepInFrame(_CONTENT_W, _FRAME_H, page2, mode="shrink"),
        PageBreak(),
        KeepInFrame(_CONTENT_W, _FRAME_H, page3, mode="shrink"),
    ]

    def footer(canvas, doc_) -> None:
        _footer(canvas, doc_, report_id, lang)

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
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
