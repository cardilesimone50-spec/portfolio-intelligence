"""Generazione del report PDF del portafoglio (reportlab).

Impaginazione coerente col brand dell'app: wordmark, accento ambra,
etichette small-caps, footer con disclaimer e numero di pagina.
"""

from datetime import datetime
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

_AMBER = colors.HexColor("#f7a600")
_INK = colors.HexColor("#14171e")
_MUTED = colors.HexColor("#6b7280")
_ROW = colors.HexColor("#f7f8fa")
_GREEN = colors.HexColor("#0e9f6e")
_RED = colors.HexColor("#dc2626")
_LINE = colors.HexColor("#e5e7eb")


def _clean(text: str) -> str:
    """Toglie il markdown (**) dalle frasi degli insight per il PDF."""
    return text.replace("**", "")


def _eur(value: float) -> str:
    return f"{value:,.0f} €".replace(",", ".")


def _footer(canvas, doc) -> None:
    canvas.saveState()
    width, _ = A4
    canvas.setStrokeColor(_LINE)
    canvas.setLineWidth(0.5)
    canvas.line(18 * mm, 14 * mm, width - 18 * mm, 14 * mm)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(_MUTED)
    canvas.drawString(
        18 * mm, 10 * mm,
        "Portfolio Intelligence · dati Yahoo Finance · stime storiche, "
        "non una previsione né consulenza finanziaria",
    )
    canvas.drawRightString(width - 18 * mm, 10 * mm, f"Pagina {doc.page}")
    canvas.restoreState()


def _section(title: str) -> Table:
    """Etichetta di sezione con barretta ambra, come nell'app."""
    bar = Table(
        [["", title.upper()]],
        colWidths=[1.2 * mm, 160 * mm],
        rowHeights=[5 * mm],
    )
    bar.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, 0), _AMBER),
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


def build_report(
    portfolio_name: str,
    positions: dict[str, float],
    period: str,
    cum_return: float,
    health_score: int,
    metrics: dict[str, str],
    insights: list[str],
    suggestions: list[str],
    names: dict[str, str] | None = None,
) -> bytes:
    """Costruisce il PDF e lo restituisce come bytes (per il download)."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm, topMargin=14 * mm, bottomMargin=20 * mm,
        title="Portfolio Intelligence — Health Report",
    )
    styles = getSampleStyleSheet()
    wordmark = ParagraphStyle(
        "wordmark", parent=styles["Normal"], fontSize=9, textColor=_MUTED,
        fontName="Helvetica-Bold",
    )
    h1 = ParagraphStyle(
        "h1", parent=styles["Title"], fontSize=24, alignment=0,
        textColor=_INK, spaceBefore=6, spaceAfter=0, leading=28,
    )
    subtitle = ParagraphStyle(
        "sub", parent=styles["Normal"], fontSize=10, textColor=_MUTED, spaceAfter=12
    )
    body = ParagraphStyle(
        "body", parent=styles["Normal"], fontSize=10, leading=15, textColor=_INK
    )

    total = sum(positions.values())
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    names = names or {}
    health_color = _GREEN if health_score >= 67 else _AMBER if health_score >= 34 else _RED
    return_color = _GREEN if cum_return >= 0 else _RED

    story = [
        Paragraph("PORTFOLIO INTELLIGENCE", wordmark),
        HRFlowable(width="100%", thickness=2, color=_AMBER, spaceAfter=10),
        Paragraph("Portfolio Health Report", h1),
        Paragraph(f"{portfolio_name} · generato il {now}", subtitle),
    ]

    kpi = Table(
        [
            ["HEALTH SCORE", "VALORE STIMATO", f"RENDIMENTO ({period.upper()})",
             "INVESTIMENTO"],
            [
                f"{health_score}/100",
                _eur(total * (1 + cum_return)),
                f"{cum_return:+.1%}",
                _eur(total),
            ],
        ],
        colWidths=[43 * mm] * 4,
    )
    kpi.setStyle(
        TableStyle(
            [
                ("TEXTCOLOR", (0, 0), (-1, 0), _MUTED),
                ("FONTSIZE", (0, 0), (-1, 0), 7),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 1), (-1, 1), 16),
                ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
                ("TEXTCOLOR", (0, 1), (0, 1), health_color),
                ("TEXTCOLOR", (2, 1), (2, 1), return_color),
                ("TEXTCOLOR", (1, 1), (1, 1), _INK),
                ("TEXTCOLOR", (3, 1), (3, 1), _INK),
                ("TOPPADDING", (0, 1), (-1, 1), 5),
                ("BOTTOMPADDING", (0, 1), (-1, 1), 8),
                ("LINEBELOW", (0, 1), (-1, 1), 0.5, _LINE),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    story += [kpi, Spacer(1, 14)]

    story += [_section("Composizione"), Spacer(1, 5)]
    rows = [["Titolo", "Società", "Importo", "Peso"]] + [
        [
            ticker,
            names.get(ticker, "")[:38],
            _eur(amount),
            f"{amount / total:.1%}",
        ]
        for ticker, amount in sorted(positions.items(), key=lambda kv: -kv[1])
    ]
    composition = Table(rows, colWidths=[22 * mm, 76 * mm, 34 * mm, 20 * mm])
    composition.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 8),
                ("TEXTCOLOR", (0, 0), (-1, 0), _MUTED),
                ("FONTSIZE", (0, 1), (-1, -1), 9.5),
                ("TEXTCOLOR", (0, 1), (-1, -1), _INK),
                ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
                ("TEXTCOLOR", (1, 1), (1, -1), _MUTED),
                ("LINEBELOW", (0, 0), (-1, 0), 0.75, _AMBER),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _ROW]),
                ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story += [composition, Spacer(1, 14)]

    story += [_section("Metriche di rischio"), Spacer(1, 5)]
    metric_items = list(metrics.items())
    half = (len(metric_items) + 1) // 2
    left, right = metric_items[:half], metric_items[half:]
    grid = []
    for i in range(half):
        row = [left[i][0], left[i][1]]
        row += [right[i][0], right[i][1]] if i < len(right) else ["", ""]
        grid.append(row)
    metrics_table = Table(grid, colWidths=[45 * mm, 31 * mm, 45 * mm, 31 * mm])
    metrics_table.setStyle(
        TableStyle(
            [
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("TEXTCOLOR", (0, 0), (0, -1), _MUTED),
                ("TEXTCOLOR", (2, 0), (2, -1), _MUTED),
                ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"),
                ("FONTNAME", (3, 0), (3, -1), "Helvetica-Bold"),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("ALIGN", (3, 0), (3, -1), "RIGHT"),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, _ROW]),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story += [metrics_table, Spacer(1, 14)]

    story += [_section("Punti di attenzione"), Spacer(1, 5)]
    for insight in insights:
        story.append(Paragraph(f"–&nbsp;&nbsp;{_clean(insight)}", body))
        story.append(Spacer(1, 3))
    story.append(Spacer(1, 10))

    story += [_section("Suggerimenti"), Spacer(1, 5)]
    for suggestion in suggestions:
        story.append(Paragraph(f"–&nbsp;&nbsp;{_clean(suggestion)}", body))
        story.append(Spacer(1, 3))

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()
