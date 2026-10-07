"""Elementi comuni dei report PDF (Investor e Advisor): stili, tabelle, grafici, piè di pagina.

Solo grafica vettoriale reportlab, nessuna immagine: i PDF restano leggeri e
nitidi a qualunque zoom. Numeri e date passano da portfolio_intelligence/
formatting.py con la lingua del documento, come nell'interfaccia.
"""

from collections.abc import Callable
from dataclasses import dataclass, field

import pandas as pd
from reportlab.graphics.shapes import Drawing, Line, Polygon, PolyLine, Rect, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.platypus import Paragraph, Table, TableStyle

from portfolio_intelligence.analytics.report_metrics import ReportMetrics
from portfolio_intelligence.config import HEALTH_SCORE_FAIR, HEALTH_SCORE_GOOD
from portfolio_intelligence.data.benchmarks import BENCHMARKS, DEFAULT_BENCHMARK
from portfolio_intelligence.formatting import fmt_date, fmt_eur, fmt_pct
from portfolio_intelligence.i18n import t_in

ACCENT = colors.HexColor("#1E40AF")
INK = colors.HexColor("#14171e")
MUTED = colors.HexColor("#5b6472")
ROW = colors.HexColor("#f6f7f9")
GREEN = colors.HexColor("#047857")
AMBER = colors.HexColor("#b45309")
RED = colors.HexColor("#b91c1c")
LINE = colors.HexColor("#e2e5ea")
ACCENT_SOFT = colors.Color(30 / 255, 64 / 255, 175 / 255, alpha=0.30)
RED_SOFT = colors.Color(185 / 255, 28 / 255, 28 / 255, alpha=0.14)
BAND = colors.Color(30 / 255, 64 / 255, 175 / 255, alpha=0.12)

MARGIN = 18 * mm
CONTENT_W = A4[0] - 2 * MARGIN  # 174 mm
FRAME_H = 254 * mm  # altezza utile per pagina con i margini dei report

LEVEL_COLORS = {"low": GREEN, "moderate": INK, "elevated": AMBER, "high": RED, "na": MUTED}


@dataclass
class ReportInput:
    """Tutto ciò che serve ai due report, già calcolato (nessun accesso a rete o DB).

    `positions` sono gli importi per titolo nella valuta del report;
    `pf_value`/`bench_value` le serie di valore normalizzate (1 = inizio
    finestra); `projection` il risultato Monte Carlo (solo Advisor e copia per
    il cliente predisposta dal consulente), `monitoring` i controlli della
    Panoramica Advisor già formattati.
    """

    portfolio_name: str
    positions: dict[str, float]
    period: str
    metrics: ReportMetrics
    pf_value: pd.Series
    bench_value: pd.Series | None
    health: int
    breakdown: dict[str, float]
    executive: str
    lang: str = "en"
    benchmark: str = BENCHMARKS[DEFAULT_BENCHMARK].label  # etichetta del benchmark del cliente
    in_eur: bool = True
    names: dict[str, str] = field(default_factory=dict)
    sector_of: dict[str, str] = field(default_factory=dict)
    monthly: pd.Series | None = None
    bench_monthly: pd.Series | None = None
    per_ticker_returns: pd.Series | None = None
    per_ticker_pnl: pd.Series | None = None
    observations: list[str] = field(default_factory=list)
    what_if: list[str] = field(default_factory=list)
    stress: list[dict] = field(default_factory=list)
    projection: dict | None = None
    monitoring: list[dict] | None = None
    risk_profile: str | None = None
    profile_band: float | None = None
    advisor: str | None = None
    recipient: str | None = None
    risk_free: float | None = None
    invested: float | None = None
    cost_known: bool = True  # False: qualche posizione senza prezzo di carico
    pnl: float | None = None
    pnl_pct: float | None = None
    coverage_notes: list[str] = field(default_factory=list)
    price_source: str = ""
    # True quando il PDF è predisposto dal consulente (area Advisor), anche la copia per il cliente
    advisor_issued: bool = False
    # serie giornaliere e dati per le analisi di dettaglio della revisione Advisor
    pf_daily: pd.Series | None = None
    bench_daily: pd.Series | None = None
    returns: pd.DataFrame | None = None  # rendimenti giornalieri dei titoli
    fund: pd.DataFrame | None = None  # fondamentali per titolo
    # nome esteso della serie del benchmark, dichiarato nella metodologia
    benchmark_name: str = BENCHMARKS[DEFAULT_BENCHMARK].name

    @property
    def total(self) -> float:
        return float(sum(self.positions.values()))

    def T(self, key: str, **kwargs) -> str:
        return t_in(self.lang, key, **kwargs)

    @property
    def period_label(self) -> str:
        """Orizzonte leggibile ("1 anno"), il codice tecnico se non tradotto."""
        label = t_in(self.lang, f"period.{self.period}")
        return self.period if label == f"period.{self.period}" else label

    def eur(self, value, decimals: int = 0, signed: bool = False) -> str:
        if not self.in_eur:
            # valute di quotazione miste: importo senza simbolo
            from portfolio_intelligence.formatting import fmt_num

            return fmt_num(value, self.lang, decimals, signed)
        return fmt_eur(value, self.lang, decimals, signed)

    def pct(self, value, decimals: int = 1, signed: bool = False) -> str:
        return fmt_pct(value, self.lang, decimals, signed)

    @property
    def profile_label(self) -> str | None:
        if not self.risk_profile or self.risk_profile == "Not set":
            return None
        label = t_in(self.lang, f"prof.{self.risk_profile}")
        return self.risk_profile if label.startswith("prof.") else label


def clean(text: str) -> str:
    """Markdown ** in grassetto e escape XML per i Paragraph di reportlab."""
    escaped = str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    parts = escaped.split("**")
    return "".join(f"<b>{p}</b>" if i % 2 else p for i, p in enumerate(parts))


def thin(series: pd.Series, max_points: int = 240) -> pd.Series:
    """Sottocampiona la serie per il grafico (il PDF resta leggero), ultimo punto incluso."""
    valid = series.dropna()
    if len(valid) <= max_points:
        return valid
    step = max(1, len(valid) // max_points)
    thinned = valid.iloc[::step]
    return (
        thinned if thinned.index[-1] == valid.index[-1] else pd.concat([thinned, valid.iloc[[-1]]])
    )


# ------------------------------------------------------------------ stili


def styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    normal = base["Normal"]
    return {
        "wordmark": ParagraphStyle(
            "wordmark", parent=normal, fontSize=8, textColor=MUTED, fontName="Helvetica-Bold"
        ),
        "h1": ParagraphStyle(
            "h1",
            parent=base["Title"],
            fontSize=22,
            alignment=0,
            textColor=INK,
            spaceBefore=4,
            spaceAfter=2,
            leading=26,
        ),
        "h2": ParagraphStyle(
            "h2",
            parent=normal,
            fontSize=13,
            leading=16,
            textColor=INK,
            fontName="Helvetica-Bold",
            spaceBefore=2,
            spaceAfter=2,
        ),
        "h3": ParagraphStyle(
            "h3",
            parent=normal,
            fontSize=8.5,
            leading=11,
            textColor=INK,
            fontName="Helvetica-Bold",
            spaceBefore=4,
            spaceAfter=1,
        ),
        "sub": ParagraphStyle(
            "sub", parent=normal, fontSize=8.5, leading=12, textColor=MUTED, spaceAfter=6
        ),
        "body": ParagraphStyle("body", parent=normal, fontSize=8.8, leading=12.6, textColor=INK),
        "cell": ParagraphStyle("cell", parent=normal, fontSize=7.6, leading=9.6, textColor=INK),
        "cell_muted": ParagraphStyle(
            "cell_muted", parent=normal, fontSize=7.2, leading=9.2, textColor=MUTED
        ),
        "small": ParagraphStyle(
            "small", parent=normal, fontSize=7.6, leading=10.4, textColor=MUTED
        ),
        "caption": ParagraphStyle(
            "caption",
            parent=normal,
            fontSize=7,
            leading=9.4,
            textColor=MUTED,
            spaceBefore=2,
        ),
        "fine": ParagraphStyle(
            "fine", parent=normal, fontSize=6.3, leading=8.3, textColor=MUTED, spaceAfter=3
        ),
    }


# ------------------------------------------------------------------ pagina


class NumberedCanvas(rl_canvas.Canvas):
    """Canvas che conosce il numero totale di pagine ("Pagina 2 di 7")."""

    footer: Callable[["NumberedCanvas", int, int], None] | None = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved: list[dict] = []

    def showPage(self):  # noqa: N802 (API reportlab)
        self._saved.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._saved)
        for state in self._saved:
            self.__dict__.update(state)
            if self.footer is not None:
                self.footer(self, self._pageNumber, total)
            super().showPage()
        super().save()


def canvas_with_footer(draw: Callable[[rl_canvas.Canvas, int, int], None]) -> type:
    """Classe canvas che disegna `draw(canvas, pagina, totale)` su ogni pagina."""
    return type("FooterCanvas", (NumberedCanvas,), {"footer": staticmethod(draw)})


def draw_footer(
    canvas: rl_canvas.Canvas,
    page: int,
    total: int,
    line1: str,
    line2: str,
    page_label: str,
) -> None:
    canvas.saveState()
    width, _ = A4
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.5)
    canvas.line(MARGIN, 14.5 * mm, width - MARGIN, 14.5 * mm)
    canvas.setFont("Helvetica", 6.3)
    canvas.setFillColor(MUTED)
    label = page_label.format(n=page, total=total)
    room = width - 2 * MARGIN - canvas.stringWidth(label, "Helvetica", 6.3) - 4 * mm
    # la riga deve stare intera: se non entra si riduce il corpo invece di tagliarla
    size = 6.3
    while size > 5.0 and canvas.stringWidth(line1, "Helvetica", size) > room:
        size -= 0.1
    canvas.setFont("Helvetica", size)
    canvas.drawString(MARGIN, 11 * mm, simpleSplit(line1, "Helvetica", size, room)[0])
    canvas.setFont("Helvetica", 6.3)
    canvas.drawRightString(width - MARGIN, 11 * mm, label)
    # avvertenze su al massimo due righe dentro i margini, in qualunque lingua
    canvas.setFont("Helvetica", 6.0)
    for i, text in enumerate(simpleSplit(line2, "Helvetica", 6.0, width - 2 * MARGIN)[:2]):
        canvas.drawString(MARGIN, (7.6 - 2.6 * i) * mm, text)
    canvas.restoreState()


def draw_brand(
    canvas: rl_canvas.Canvas, x: float, y: float, size: float = 4.4 * mm, font: float = 8.2
) -> float:
    """Simbolo e scritta SMARTEEFINANCE con base in (x, y); restituisce la x finale."""
    from portfolio_intelligence.ui.brand import FACETS

    canvas.saveState()
    scale = size / 100
    for points, color in FACETS:
        path = canvas.beginPath()
        first, *rest = [(x + px * scale, y + (100 - py) * scale) for px, py in points]
        path.moveTo(*first)
        for point in rest:
            path.lineTo(*point)
        path.close()
        canvas.setFillColor(colors.HexColor(color))
        canvas.drawPath(path, stroke=0, fill=1)
    text_x = x + size + 2.2 * mm
    text_y = y + size * 0.22
    canvas.setFillColor(INK)
    canvas.setFont("Helvetica", font)
    canvas.drawString(text_x, text_y, "SMARTEE")
    text_x += canvas.stringWidth("SMARTEE", "Helvetica", font)
    canvas.setFillColor(ACCENT)
    canvas.setFont("Helvetica-Bold", font)
    canvas.drawString(text_x, text_y, "FINANCE")
    text_x += canvas.stringWidth("FINANCE", "Helvetica-Bold", font)
    canvas.restoreState()
    return text_x


def draw_header(canvas: rl_canvas.Canvas, right: str) -> None:
    """Intestazione di ogni pagina: marchio a sinistra, documento e cliente a destra."""
    width, height = A4
    top = height - 12.5 * mm
    draw_brand(canvas, MARGIN, top)
    canvas.saveState()
    canvas.setFont("Helvetica", 6.8)
    canvas.setFillColor(MUTED)
    canvas.drawRightString(width - MARGIN, top + 1.1 * mm, right)
    canvas.setStrokeColor(ACCENT)
    canvas.setLineWidth(0.8)
    canvas.line(MARGIN, top - 2.2 * mm, width - MARGIN, top - 2.2 * mm)
    canvas.restoreState()


def section(title: str, width: float = CONTENT_W) -> Table:
    """Etichetta di sezione: barretta blu e titolo in maiuscoletto.

    Il titolo resta sull'oggetto (`toc_title`): l'indice del documento lo raccoglie.
    """
    bar = Table([["", title.upper()]], colWidths=[1.2 * mm, width - 1.2 * mm], rowHeights=[5 * mm])
    bar.toc_title = title
    bar.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, 0), ACCENT),
                ("TEXTCOLOR", (1, 0), (1, 0), INK),
                ("FONTNAME", (1, 0), (1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (1, 0), (1, 0), 7.8),
                ("LEFTPADDING", (1, 0), (1, 0), 6),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return bar


def data_table(
    rows: list[list],
    widths: list[float],
    right_from: int | None = 1,
    font_size: float = 7.8,
    zebra: bool = True,
    bold_first_col: bool = False,
    extra: list | None = None,
) -> Table:
    """Tabella dati: intestazione con filetto blu, righe alterne, numeri allineati a destra."""
    table = Table(rows, colWidths=widths, repeatRows=1)
    style = [
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 6.8),
        ("TEXTCOLOR", (0, 0), (-1, 0), MUTED),
        ("LINEBELOW", (0, 0), (-1, 0), 0.75, ACCENT),
        ("FONTSIZE", (0, 1), (-1, -1), font_size),
        ("TEXTCOLOR", (0, 1), (-1, -1), INK),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2.6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.6),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("LINEBELOW", (0, -1), (-1, -1), 0.4, LINE),
    ]
    if right_from is not None and right_from < len(widths):
        style.append(("ALIGN", (right_from, 0), (-1, -1), "RIGHT"))
    if zebra and len(rows) > 2:
        style.append(("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ROW]))
    if bold_first_col:
        style.append(("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"))
    table.setStyle(TableStyle(style + (extra or [])))
    return table


def kpi_grid(cells: list[tuple[str, str, str]], cols: int = 4, colors_by_index=None) -> Table:
    """Griglia di indicatori: etichetta (maiuscoletto), valore, nota; filetti tra le celle."""
    s = styles()
    label_style = ParagraphStyle(
        "kpi_label", parent=s["cell_muted"], fontSize=6, leading=7.6, fontName="Helvetica-Bold"
    )
    note_style = ParagraphStyle("kpi_note", parent=s["cell_muted"], fontSize=6.4, leading=8)
    colors_by_index = colors_by_index or {}
    grid: list[list] = []
    for start in range(0, len(cells), cols):
        row: list = []
        for i, (label, value, note) in enumerate(cells[start : start + cols]):
            color = colors_by_index.get(start + i, INK)
            value_style = ParagraphStyle(
                f"kpi_value_{start + i}",
                parent=s["body"],
                fontSize=11.5,
                leading=14,
                fontName="Helvetica-Bold",
                textColor=color,
            )
            row.append(
                [
                    Paragraph(clean(label.upper()), label_style),
                    Paragraph(clean(value), value_style),
                    Paragraph(clean(note), note_style),
                ]
            )
        while len(row) < cols:
            row.append("")
        grid.append(row)
    table = Table(grid, colWidths=[CONTENT_W / cols] * cols)
    table.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.5, LINE),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def callout(paragraphs: list, color=ACCENT, width: float = CONTENT_W) -> Table:
    """Riquadro con barretta colorata a sinistra (verifiche, avvertenze, indicatori)."""
    box = Table([["", paragraphs]], colWidths=[1.2 * mm, width - 1.2 * mm])
    box.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, 0), color),
                ("BACKGROUND", (1, 0), (1, 0), ROW),
                ("TOPPADDING", (1, 0), (1, 0), 4),
                ("BOTTOMPADDING", (1, 0), (1, 0), 5),
                ("LEFTPADDING", (1, 0), (1, 0), 7),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return box


def side_by_side(left: list, right: list, gap: float = 6 * mm) -> Table:
    """Due colonne di contenuto della stessa larghezza."""
    half = (CONTENT_W - gap) / 2
    table = Table([[left, right]], colWidths=[half + gap / 2, half + gap / 2])
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (0, 0), gap / 2),
                ("RIGHTPADDING", (1, 0), (1, 0), 0),
                ("LEFTPADDING", (1, 0), (1, 0), gap / 2),
            ]
        )
    )
    return table


HALF_W = (CONTENT_W - 6 * mm) / 2


def score_color(score: float):
    return GREEN if score >= HEALTH_SCORE_GOOD else AMBER if score >= HEALTH_SCORE_FAIR else RED


# ------------------------------------------------------------------ grafici vettoriali


def _axis_levels(low: float, high: float, steps: int = 4) -> list[float]:
    """Tacche dell'asse a passo "tondo" (1, 2, 2,5, 5 × 10^k) dentro [low, high]."""
    import math

    if high <= low:
        high = low + 1
    raw = (high - low) / steps
    magnitude = 10 ** math.floor(math.log10(raw))
    step = next(m * magnitude for m in (1, 2, 2.5, 5, 10) if m * magnitude >= raw)
    first = math.ceil(low / step) * step
    levels = []
    value = first
    while value <= high + 1e-9:
        levels.append(round(value, 10))
        value += step
    return levels or [low, high]


def line_chart(
    series: list[tuple[str, pd.Series, object, bool]],
    y_label: Callable[[float], str],
    width: float = CONTENT_W,
    height: float = 56 * mm,
    reference: float | None = None,
) -> Drawing:
    """Serie temporali a linee: (etichetta, serie, colore, tratteggiata).

    `reference` disegna una linea orizzontale punteggiata (es. base 100 o
    capitale investito).
    """
    drawing = Drawing(width, height)
    data = [
        (label, thin(s), color, dashed)
        for label, s, color, dashed in series
        if len(s.dropna()) >= 2
    ]
    if not data:
        return drawing
    left, right, bottom, top = 17 * mm, 2 * mm, 6 * mm, 7 * mm
    plot_w, plot_h = width - left - right, height - bottom - top
    low = min(float(s.min()) for _, s, _, _ in data)
    high = max(float(s.max()) for _, s, _, _ in data)
    if reference is not None:
        low, high = min(low, reference), max(high, reference)
    pad = (high - low) * 0.06 or abs(high) * 0.02 or 1
    low, high = low - pad, high + pad
    start = min(s.index[0] for _, s, _, _ in data)
    end = max(s.index[-1] for _, s, _, _ in data)
    span = max((pd.Timestamp(end) - pd.Timestamp(start)).days, 1)

    def x_at(date) -> float:
        return left + plot_w * (pd.Timestamp(date) - pd.Timestamp(start)).days / span

    def y_at(value: float) -> float:
        return bottom + (value - low) / (high - low) * plot_h

    for level in _axis_levels(low, high):
        y = y_at(level)
        drawing.add(Line(left, y, left + plot_w, y, strokeColor=LINE, strokeWidth=0.4))
        drawing.add(
            String(
                left - 2 * mm,
                y - 1,
                y_label(level),
                fontName="Helvetica",
                fontSize=6.2,
                fillColor=MUTED,
                textAnchor="end",
            )
        )
    if reference is not None:
        drawing.add(
            Line(
                left,
                y_at(reference),
                left + plot_w,
                y_at(reference),
                strokeColor=MUTED,
                strokeWidth=0.6,
                strokeDashArray=[1, 2],
            )
        )
    for _label, s, color, dashed in data:
        points: list[float] = []
        for date, value in s.items():
            points += [x_at(date), y_at(float(value))]
        drawing.add(
            PolyLine(
                points,
                strokeColor=color,
                strokeWidth=1.0 if dashed else 1.5,
                strokeDashArray=[3, 2] if dashed else None,
            )
        )
    drawing.add(
        String(left, 1, fmt_date(start), fontName="Helvetica", fontSize=6.2, fillColor=MUTED)
    )
    drawing.add(
        String(
            left + plot_w,
            1,
            fmt_date(end),
            fontName="Helvetica",
            fontSize=6.2,
            fillColor=MUTED,
            textAnchor="end",
        )
    )
    x = left + 2 * mm
    for label, _s, color, dashed in data:
        drawing.add(
            Rect(x, height - 4.5 * mm, 4 * mm, 1.2 * mm, fillColor=color, strokeColor=None)
        )
        drawing.add(
            String(
                x + 5 * mm,
                height - 5 * mm,
                label,
                fontName="Helvetica",
                fontSize=6.4,
                fillColor=MUTED if dashed else INK,
            )
        )
        x += 7 * mm + 1.6 * mm * max(len(label), 6)
    return drawing


def underwater_chart(
    value: pd.Series, width: float = HALF_W, height: float = 40 * mm, note: str = ""
) -> Drawing:
    """Distanza dal massimo precedente (underwater), area rossa."""
    drawing = Drawing(width, height)
    valid = thin(value)
    if len(valid) < 2:
        return drawing
    dd = valid / valid.cummax() - 1
    left, bottom, top = 11 * mm, 5 * mm, 3 * mm
    plot_w, plot_h = width - left - 2 * mm, height - bottom - top
    low = min(float(dd.min()), -0.01) * 1.08

    def y_at(v: float) -> float:
        return bottom + plot_h * (1 - v / low)

    n = len(dd)
    xs = [left + plot_w * i / max(1, n - 1) for i in range(n)]
    top_y = y_at(0)
    poly = [xs[0], top_y]
    line_pts: list[float] = []
    for x, v in zip(xs, dd.to_numpy(dtype=float), strict=True):
        poly += [x, y_at(v)]
        line_pts += [x, y_at(v)]
    poly += [xs[-1], top_y]
    drawing.add(Polygon(poly, fillColor=RED_SOFT, strokeColor=None))
    drawing.add(PolyLine(line_pts, strokeColor=RED, strokeWidth=0.9))
    drawing.add(Line(left, top_y, left + plot_w, top_y, strokeColor=LINE, strokeWidth=0.5))
    for level in (0.0, low / 2, low):
        drawing.add(
            String(
                left - 1.5 * mm,
                y_at(level) - 1,
                f"{level:.0%}",
                fontName="Helvetica",
                fontSize=6,
                fillColor=MUTED,
                textAnchor="end",
            )
        )
    if note:
        drawing.add(
            String(
                left + plot_w,
                1,
                note,
                fontName="Helvetica",
                fontSize=6,
                fillColor=MUTED,
                textAnchor="end",
            )
        )
    return drawing


def monthly_chart(
    monthly: pd.Series, lang: str, width: float = HALF_W, height: float = 40 * mm
) -> Drawing:
    """Rendimenti mensili a barre, verde/rosso secondo il segno; mesi in formato numerico."""
    drawing = Drawing(width, height)
    valid = monthly.dropna()
    if valid.empty:
        return drawing
    left, bottom, top = 4 * mm, 6 * mm, 4 * mm
    plot_w, plot_h = width - left - 2 * mm, height - bottom - top
    biggest = max(abs(float(valid.max())), abs(float(valid.min())), 0.01)
    zero_y = bottom + plot_h / 2
    scale = (plot_h / 2 - 1) / biggest
    slot = plot_w / max(1, len(valid))
    bar_w = slot * 0.62
    drawing.add(Line(left, zero_y, left + plot_w, zero_y, strokeColor=LINE, strokeWidth=0.5))
    for i, (label, value) in enumerate(valid.items()):
        x = left + slot * i + (slot - bar_w) / 2
        h = float(value) * scale
        drawing.add(
            Rect(
                x,
                zero_y + min(0, h),
                bar_w,
                abs(h),
                fillColor=GREEN if value >= 0 else RED,
                strokeColor=None,
            )
        )
        drawing.add(
            String(
                x + bar_w / 2,
                zero_y + h + (1.5 * mm if value >= 0 else -3 * mm),
                fmt_pct(value, lang, 0, signed=True),
                fontName="Helvetica",
                fontSize=5.3,
                fillColor=MUTED,
                textAnchor="middle",
            )
        )
        drawing.add(
            String(
                x + bar_w / 2,
                1,
                pd.Timestamp(label).strftime("%m/%y"),
                fontName="Helvetica",
                fontSize=5.3,
                fillColor=MUTED,
                textAnchor="middle",
            )
        )
    return drawing


def weight_risk_chart(
    weights: pd.Series,
    risk: pd.Series,
    lang: str,
    legend_weight: str,
    legend_risk: str,
    width: float = HALF_W,
    max_rows: int = 8,
) -> Drawing:
    """Peso sul capitale contro contributo al rischio, coppie di barre orizzontali."""
    top_weights = weights.sort_values(ascending=False).head(max_rows)
    row_h, legend_h = 7.5 * mm, 6 * mm
    height = row_h * len(top_weights) + legend_h
    drawing = Drawing(width, height)
    left = 14 * mm
    plot_w = width - left - 14 * mm
    biggest = max(float(top_weights.max()), float(risk.max()) if len(risk.dropna()) else 0, 0.01)
    for i, (ticker, weight) in enumerate(top_weights.items()):
        base_y = height - legend_h - row_h * (i + 1)
        r = float(risk.get(ticker, float("nan")))
        drawing.add(
            String(
                left - 2 * mm,
                base_y + 2.4 * mm,
                str(ticker)[:8],
                fontName="Helvetica-Bold",
                fontSize=7,
                fillColor=INK,
                textAnchor="end",
            )
        )
        w_len = plot_w * float(weight) / biggest
        drawing.add(
            Rect(left, base_y + 3.8 * mm, w_len, 2.2 * mm, fillColor=ACCENT_SOFT, strokeColor=None)
        )
        drawing.add(
            String(
                left + w_len + 1.5 * mm,
                base_y + 4.1 * mm,
                fmt_pct(weight, lang),
                fontName="Helvetica",
                fontSize=5.8,
                fillColor=MUTED,
            )
        )
        if r == r:
            r_len = plot_w * r / biggest
            drawing.add(
                Rect(left, base_y + 1 * mm, r_len, 2.2 * mm, fillColor=ACCENT, strokeColor=None)
            )
            drawing.add(
                String(
                    left + r_len + 1.5 * mm,
                    base_y + 1.3 * mm,
                    fmt_pct(r, lang),
                    fontName="Helvetica",
                    fontSize=5.8,
                    fillColor=MUTED,
                )
            )
    ly = height - 4 * mm
    drawing.add(Rect(left, ly, 4 * mm, 2 * mm, fillColor=ACCENT_SOFT, strokeColor=None))
    drawing.add(
        String(
            left + 5 * mm, ly, legend_weight, fontName="Helvetica", fontSize=6.2, fillColor=MUTED
        )
    )
    drawing.add(Rect(left + 32 * mm, ly, 4 * mm, 2 * mm, fillColor=ACCENT, strokeColor=None))
    drawing.add(
        String(
            left + 37 * mm, ly, legend_risk, fontName="Helvetica", fontSize=6.2, fillColor=MUTED
        )
    )
    return drawing


def bar_list_chart(
    values: pd.Series,
    lang: str,
    width: float = HALF_W,
    max_rows: int = 7,
    other_label: str = "Other",
) -> Drawing:
    """Allocazione (settori, valute) a barre orizzontali ordinate per peso."""
    top = values.sort_values(ascending=False).head(max_rows)
    other = float(values.sum() - top.sum())
    if other > 0.001:
        top = pd.concat([top, pd.Series({other_label: other})])
    row_h = 6.5 * mm
    height = row_h * max(len(top), 1)
    drawing = Drawing(width, height)
    left = 34 * mm
    plot_w = width - left - 13 * mm
    biggest = max(float(top.max()) if len(top) else 0, 0.01)
    for i, (name, weight) in enumerate(top.items()):
        base_y = height - row_h * (i + 1) + 2 * mm
        drawing.add(
            String(
                left - 2 * mm,
                base_y + 0.4 * mm,
                str(name)[:24],
                fontName="Helvetica",
                fontSize=6.8,
                fillColor=MUTED,
                textAnchor="end",
            )
        )
        length = plot_w * float(weight) / biggest
        drawing.add(
            Rect(
                left,
                base_y,
                length,
                2.6 * mm,
                fillColor=ACCENT if i == 0 else ACCENT_SOFT,
                strokeColor=None,
            )
        )
        drawing.add(
            String(
                left + length + 1.5 * mm,
                base_y + 0.4 * mm,
                fmt_pct(weight, lang, 1),
                fontName="Helvetica-Bold",
                fontSize=6.3,
                fillColor=INK,
            )
        )
    return drawing


def score_bars(breakdown: dict[str, float], width: float = HALF_W) -> Drawing:
    """Componenti del punteggio composito come barre 0-100."""
    row_h = 6 * mm
    height = row_h * max(len(breakdown), 1)
    drawing = Drawing(width, height)
    left = 30 * mm
    plot_w = width - left - 10 * mm
    for i, (label, score) in enumerate(breakdown.items()):
        base_y = height - row_h * (i + 1) + 1.5 * mm
        drawing.add(
            String(
                left - 2 * mm,
                base_y + 0.5 * mm,
                str(label),
                fontName="Helvetica",
                fontSize=6.8,
                fillColor=MUTED,
                textAnchor="end",
            )
        )
        drawing.add(
            Rect(left, base_y, plot_w, 2.4 * mm, fillColor=ROW, strokeColor=LINE, strokeWidth=0.3)
        )
        if score == score:
            drawing.add(
                Rect(
                    left,
                    base_y,
                    plot_w * min(100, max(0, score)) / 100,
                    2.4 * mm,
                    fillColor=score_color(score),
                    strokeColor=None,
                )
            )
        drawing.add(
            String(
                left + plot_w + 2 * mm,
                base_y + 0.3 * mm,
                f"{score:.0f}" if score == score else "–",
                fontName="Helvetica-Bold",
                fontSize=6.8,
                fillColor=INK,
            )
        )
    return drawing


def fan_chart(
    paths: pd.DataFrame,
    y_label: Callable[[float], str],
    year_label: Callable[[int], str],
    width: float = CONTENT_W,
    height: float = 52 * mm,
) -> Drawing:
    """Ventaglio Monte Carlo: bande p10-p90 e p25-p75, mediana; indice in anni."""
    drawing = Drawing(width, height)
    needed = {"p10", "p25", "p50", "p75", "p90"}
    if paths is None or paths.empty or not needed <= set(paths.columns):
        return drawing
    left, right, bottom, top = 17 * mm, 3 * mm, 6 * mm, 3 * mm
    plot_w, plot_h = width - left - right, height - bottom - top
    low = float(paths["p10"].min()) * 0.97
    high = float(paths["p90"].max()) * 1.03
    years = paths.index.to_numpy(dtype=float)
    horizon = max(float(years[-1]), 1e-9)

    def x_at(y: float) -> float:
        return left + plot_w * y / horizon

    def y_at(v: float) -> float:
        return bottom + (v - low) / (high - low) * plot_h

    for level in _axis_levels(low, high):
        drawing.add(
            Line(left, y_at(level), left + plot_w, y_at(level), strokeColor=LINE, strokeWidth=0.4)
        )
        drawing.add(
            String(
                left - 2 * mm,
                y_at(level) - 1,
                y_label(level),
                fontName="Helvetica",
                fontSize=6.2,
                fillColor=MUTED,
                textAnchor="end",
            )
        )
    for lo, hi, fill in (("p10", "p90", BAND), ("p25", "p75", ACCENT_SOFT)):
        upper = [(x_at(y), y_at(v)) for y, v in zip(years, paths[hi], strict=True)]
        lower = [(x_at(y), y_at(v)) for y, v in zip(years, paths[lo], strict=True)][::-1]
        drawing.add(
            Polygon([c for pt in upper + lower for c in pt], fillColor=fill, strokeColor=None)
        )
    median = [c for y, v in zip(years, paths["p50"], strict=True) for c in (x_at(y), y_at(v))]
    drawing.add(PolyLine(median, strokeColor=ACCENT, strokeWidth=1.5))
    initial = float(paths["p50"].iloc[0])
    drawing.add(
        Line(
            left,
            y_at(initial),
            left + plot_w,
            y_at(initial),
            strokeColor=MUTED,
            strokeWidth=0.6,
            strokeDashArray=[1, 2],
        )
    )
    for year in range(int(horizon) + 1):
        drawing.add(
            String(
                x_at(year),
                1,
                year_label(year),
                fontName="Helvetica",
                fontSize=6.2,
                fillColor=MUTED,
                textAnchor="middle",
            )
        )
    return drawing


# ------------------------------------------------------------------ documento


def report_reference(r: ReportInput, now: str, kind: str = "investor") -> str:
    """Identificativo del documento per riferimento e tracciabilità nelle revisioni.

    Il tipo di documento entra nell'impronta: revisione e report per il cliente
    generati nello stesso minuto hanno riferimenti diversi.
    """
    import hashlib

    seed = f"{kind}|{r.portfolio_name}|{r.advisor or ''}|{now}"
    return hashlib.sha1(seed.encode()).hexdigest()[:8].upper()


def page_header(r: ReportInput, topic: str, now: str) -> list:
    s = styles()
    return [
        Paragraph(clean(topic), s["h2"]),
        Paragraph(clean(f"{r.portfolio_name} · {now}"), s["sub"]),
    ]


def render_pdf(
    story: list,
    r: ReportInput,
    title: str,
    rid: str,
    header_right: str = "",
    cover: bool = False,
    toc=None,
) -> bytes:
    """Impagina il documento: intestazione col marchio, piè di pagina legale, "Pagina n di N".

    `cover`: la prima pagina è una copertina (niente intestazione: il marchio è
    già nel corpo). `toc`: un TableOfContents nel racconto; i titoli di sezione
    lo popolano con i numeri di pagina (due passate di impaginazione).
    """
    from io import BytesIO

    from reportlab.platypus import SimpleDocTemplate

    class _Doc(SimpleDocTemplate):
        def afterFlowable(self, flowable):  # noqa: N802 (API reportlab)
            title_text = getattr(flowable, "toc_title", None)
            if title_text and toc is not None:
                self.notify("TOCEntry", (0, title_text.upper(), self.page))

    buffer = BytesIO()
    doc = _Doc(
        buffer,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        title=title,
        author="SmarteeFinance",
    )
    line1 = r.T("rep.footer1", rid=rid)
    line2 = r.T("pdf.footer_line2")
    page_label = r.T("rep.page")
    right = header_right or f"{title} · {r.portfolio_name}"

    def decorate(canvas, page: int, total: int) -> None:
        if not (cover and page == 1):
            draw_header(canvas, right)
        draw_footer(canvas, page, total, line1, line2, page_label)

    maker = canvas_with_footer(decorate)
    if toc is not None:
        doc.multiBuild(story, canvasmaker=maker)
    else:
        doc.build(story, canvasmaker=maker)
    return buffer.getvalue()


def heatmap_table(matrix: pd.DataFrame, lang: str, width: float = CONTENT_W) -> Table:
    """Matrice (es. correlazioni) con celle colorate: blu se positiva, rossa se negativa."""
    from portfolio_intelligence.formatting import fmt_num

    labels = [str(c)[:8] for c in matrix.columns]
    rows: list[list] = [[""] + labels]
    style: list = [
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 6.6),
        ("TEXTCOLOR", (0, 0), (-1, 0), MUTED),
        ("TEXTCOLOR", (0, 1), (0, -1), INK),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (1, 1), (-1, -1), 0.4, colors.white),
        ("TOPPADDING", (0, 0), (-1, -1), 2.4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.4),
    ]
    for i, (name, row) in enumerate(matrix.iterrows(), start=1):
        cells = [str(name)[:8]]
        for j, value in enumerate(row, start=1):
            v = float(value)
            cells.append(fmt_num(v, lang, 2) if v == v else "")
            if v == v:
                strength = min(1.0, abs(v))
                base = (30, 64, 175) if v >= 0 else (185, 28, 28)
                shade = colors.Color(*(1 - (1 - c / 255) * strength * 0.85 for c in base))
                style.append(("BACKGROUND", (j, i), (j, i), shade))
                if strength > 0.55:
                    style.append(("TEXTCOLOR", (j, i), (j, i), colors.white))
        rows.append(cells)
    first = 16 * mm
    cell = min((width - first) / max(1, len(labels)), 18 * mm)
    table = Table(rows, colWidths=[first] + [cell] * len(labels))
    table.setStyle(TableStyle(style))
    return table
