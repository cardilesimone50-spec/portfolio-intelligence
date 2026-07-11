"""Generazione del report PDF del portafoglio (reportlab)."""

from datetime import datetime
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

_ACCENT = colors.HexColor("#2a78d6")
_MUTED = colors.HexColor("#666666")


def _clean(text: str) -> str:
    """Toglie il markdown (**) dalle frasi degli insight per il PDF."""
    return text.replace("**", "")


def _eur(value: float) -> str:
    return f"{value:,.0f} €".replace(",", ".")


def build_report(
    portfolio_name: str,
    positions: dict[str, float],
    period: str,
    cum_return: float,
    risk_score: int,
    metrics: dict[str, str],
    insights: list[str],
    suggestions: list[str],
) -> bytes:
    """Costruisce il PDF e lo restituisce come bytes (per il download)."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm,
        title="Portfolio Intelligence Report",
    )
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Title"], fontSize=22, spaceAfter=2)
    subtitle = ParagraphStyle("sub", parent=styles["Normal"], textColor=_MUTED, spaceAfter=14)
    h2 = ParagraphStyle(
        "h2", parent=styles["Heading2"], textColor=_ACCENT, spaceBefore=14, spaceAfter=6
    )
    body = ParagraphStyle("body", parent=styles["Normal"], fontSize=10.5, leading=15)
    disclaimer = ParagraphStyle(
        "disc", parent=styles["Normal"], fontSize=8, textColor=_MUTED, spaceBefore=18
    )

    total = sum(positions.values())
    now = datetime.now().strftime("%d/%m/%Y %H:%M")

    story = [
        Paragraph("Portfolio Intelligence Report", h1),
        Paragraph(f"{portfolio_name} — generato il {now}", subtitle),
    ]

    summary = Table(
        [
            ["Investimento", "Valore stimato", "Rendimento (" + period + ")", "Rischio"],
            [
                _eur(total),
                _eur(total * (1 + cum_return)),
                f"{cum_return:+.1%}",
                f"{risk_score}/100",
            ],
        ],
        colWidths=[43 * mm] * 4,
    )
    summary.setStyle(
        TableStyle(
            [
                ("TEXTCOLOR", (0, 0), (-1, 0), _MUTED),
                ("FONTSIZE", (0, 0), (-1, 0), 8.5),
                ("FONTSIZE", (0, 1), (-1, 1), 14),
                ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
                ("TOPPADDING", (0, 1), (-1, 1), 4),
                ("LINEBELOW", (0, 0), (-1, 0), 0.25, colors.HexColor("#dddddd")),
            ]
        )
    )
    story.append(summary)

    story.append(Paragraph("Composizione", h2))
    rows = [["Titolo", "Importo", "Peso"]] + [
        [ticker, _eur(amount), f"{amount / total:.1%}"]
        for ticker, amount in sorted(positions.items(), key=lambda kv: -kv[1])
    ]
    composition = Table(rows, colWidths=[60 * mm, 45 * mm, 30 * mm])
    composition.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9.5),
                ("LINEBELOW", (0, 0), (-1, 0), 0.5, _ACCENT),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f7fa")]),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ]
        )
    )
    story.append(composition)

    story.append(Paragraph("Metriche di rischio", h2))
    metric_rows = [[name, value] for name, value in metrics.items()]
    metrics_table = Table(metric_rows, colWidths=[70 * mm, 65 * mm])
    metrics_table.setStyle(
        TableStyle(
            [
                ("FONTSIZE", (0, 0), (-1, -1), 9.5),
                ("TEXTCOLOR", (0, 0), (0, -1), _MUTED),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#f5f7fa")]),
            ]
        )
    )
    story.append(metrics_table)

    story.append(Paragraph("Punti di attenzione", h2))
    for insight in insights:
        story.append(Paragraph(f"• {_clean(insight)}", body))
        story.append(Spacer(1, 3))

    story.append(Paragraph("Suggerimenti", h2))
    for suggestion in suggestions:
        story.append(Paragraph(f"• {_clean(suggestion)}", body))
        story.append(Spacer(1, 3))

    story.append(
        Paragraph(
            "Report generato automaticamente da Portfolio Intelligence su dati "
            "Yahoo Finance. Le stime sono basate sull'andamento storico e non "
            "costituiscono una previsione né un consiglio di investimento.",
            disclaimer,
        )
    )

    doc.build(story)
    return buffer.getvalue()
