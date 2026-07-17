"""Il report PDF è sempre di 3 pagine, con le sezioni da consulente."""

from io import BytesIO

import numpy as np
import pandas as pd
import pdfplumber

from src.visualization.pdf_report import build_report

METRIC_ROWS = [
    ("Return (1y)", "+12.3%", "+10.0%", "Total change over the observation window."),
    ("Annualized return (CAGR)", "+12.3%", "+10.0%", "Compound annual growth."),
    ("Annual volatility", "18.0%", "16.0%", "Swings typical of diversified equity."),
    ("Sharpe ratio", "0.85", "0.70", "In line with diversified equity."),
    ("Sortino ratio", "1.10", "0.90", "Volatility skews to the upside."),
    ("Max drawdown", "-14.2%", "-12.0%", "Between a correction and a bear market."),
    ("VaR 95% (1 day)", "-2.1%", "-1.8%", "Historical percentile, no normality assumed."),
    ("Expected shortfall 95%", "-3.0%", "-2.5%", "Average loss on the worst 5% of days."),
    ("Beta vs QQQ", "1.05", "—", "You move broadly in line with QQQ."),
    ("Alpha vs QQQ", "+1.2%/yr", "—", "Excess return not explained by the benchmark."),
    ("Average correlation", "0.45", "—", "Average diversification within the same market."),
]


def _synthetic_series(days: int = 300) -> pd.Series:
    rng = np.random.default_rng(7)
    index = pd.bdate_range("2025-01-02", periods=days)
    return pd.Series((1 + rng.normal(0.0004, 0.012, days)).cumprod(), index=index)


def _full_report() -> bytes:
    pf_value = _synthetic_series()
    monthly = pf_value.resample("ME").last().pct_change().dropna().tail(12)
    return build_report(
        portfolio_name="Test portfolio",
        positions={"AAPL": 5000.0, "MSFT": 3000.0, "NVDA": 2000.0},
        period="1y",
        cum_return=0.123,
        health_score=72,
        metric_rows=METRIC_ROWS,
        insights=["Risk is **concentrated** in NVDA.", "USD exposure is high."],
        suggestions=["Halve NVDA and redistribute.", "Add a low-correlation holding."],
        names={"AAPL": "Apple Inc.", "MSFT": "Microsoft Corp.", "NVDA": "NVIDIA Corp."},
        advisor="advisor@example.com",
        risk_profile="Moderate",
        benchmark="QQQ",
        executive="Over the period (1y) the portfolio returned +12.3%.",
        suitability={
            "ok": False,
            "text": "Observed annual volatility 18.0% vs the 18% threshold declared "
            "for a moderate profile.",
        },
        annual_return=0.123,
        pf_value=pf_value,
        bench_value=_synthetic_series() * 0.98,
        monthly=monthly,
        contributions=pd.Series({"NVDA": 0.55, "AAPL": 0.30, "MSFT": 0.15}),
        sector_weights=pd.Series({"Technology": 0.8, "Consumer Cyclical": 0.2}),
        coverage_notes=["NVDA priced only from 12/03/2025 — its metrics use the shorter overlap"],
        breakdown={
            "Diversification": 60.0,
            "Concentration": 45.0,
            "Volatility": 70.0,
            "Currency": 30.0,
            "Drawdown": 80.0,
            "Quality": 75.0,
        },
        per_ticker_returns=pd.Series({"AAPL": 0.10, "MSFT": 0.08, "NVDA": 0.30}),
        scenario={"label": "NVDA drops 20%", "direct": -0.04, "total": -0.065},
        risk_free=0.042,
    )


def test_report_has_exactly_three_pages_with_advisor_sections():
    data = _full_report()
    assert data.startswith(b"%PDF")
    with pdfplumber.open(BytesIO(data)) as pdf:
        assert len(pdf.pages) == 3
        page1 = pdf.pages[0].extract_text()
        page2 = pdf.pages[1].extract_text()
        page3 = pdf.pages[2].extract_text()
    assert "EXECUTIVE SUMMARY" in page1
    assert "HOLDINGS" in page1
    assert "prepared by advisor@example.com" in page1
    assert "observation window" in page1
    assert "Risk profile check" in page1
    assert "MiFID II suitability" in page1  # il software non rivendica l'adeguatezza
    assert "Data coverage" in page1
    assert "Sharpe ratio" in page2
    assert "Expected shortfall" in page2
    assert "HEALTH SCORE" in page2.upper()
    assert "ALLOCATION BY SECTOR" in page3
    assert "Technology" in page3
    assert "STRESS SCENARIO" in page3
    assert "METHODOLOGY" in page3
    assert "OBSERVATIONS & TALKING POINTS" in page3
    # avvertenze obbligatorie nel footer di OGNI pagina + note legali in pagina 3
    for page in (page1, page2, page3):
        assert "Past performance is not a reliable indicator" in page
        assert "Ref." in page
    assert "gross of transaction costs" in page3
    assert "not intended for public distribution" in page3
    # il markdown ** non deve finire nel PDF
    assert "**" not in page3


def test_report_shows_real_gain_from_cost_basis():
    data = build_report(
        portfolio_name="P&L portfolio",
        positions={"AAPL": 6000.0, "MSFT": 4000.0},
        period="1y",
        cum_return=0.10,
        health_score=70,
        metric_rows=METRIC_ROWS[:3],
        insights=[],
        suggestions=[],
        invested=8000.0,
        pnl=2000.0,
        pnl_pct=0.25,
        per_ticker_pnl=pd.Series({"AAPL": 1500.0, "MSFT": 500.0}),
    )
    with pdfplumber.open(BytesIO(data)) as pdf:
        assert len(pdf.pages) == 3
        page1 = pdf.pages[0].extract_text()
        page3 = pdf.pages[2].extract_text()
    assert "GAIN (+25.0%)" in page1
    assert "+2.000 €" in page1
    assert "8.000 €" in page1  # investito = carico, non valore attuale
    assert "+1.500 €" in page1  # P&L per posizione
    assert "quantity × (current price" in page3  # metodologia del P&L


def test_report_in_italian_translates_sections_and_legal_footer():
    pf_value = _synthetic_series()
    data = build_report(
        portfolio_name="Portafoglio test",
        positions={"AAPL": 5000.0, "MSFT": 3000.0},
        period="1y",
        cum_return=0.10,
        health_score=70,
        metric_rows=[("Sharpe ratio", "0.85", "0.70", "In linea con l'azionario.")],
        insights=["Rischio concentrato su **AAPL**."],
        suggestions=["Valutare una riduzione del peso."],
        risk_profile="Moderate",
        suitability={"ok": True, "text": "Volatilità 15% contro soglia 18%."},
        pf_value=pf_value,
        sector_weights=pd.Series({"Technology": 1.0}),
        lang="it",
    )
    with pdfplumber.open(BytesIO(data)) as pdf:
        assert len(pdf.pages) == 3
        page1 = pdf.pages[0].extract_text()
        page3 = pdf.pages[2].extract_text()
    assert "SINTESI ESECUTIVA" in page1
    assert "POSIZIONI" in page1
    assert "profilo moderato" in page1
    assert "Verifica del profilo di rischio" in page1
    assert "METODOLOGIA, ASSUNZIONI E AVVERTENZE" in page3
    assert "I rendimenti passati non sono un indicatore affidabile" in page1
    assert "consulenza in materia di investimenti" in page3


def test_report_flags_sub_year_window_in_methodology():
    short_value = _synthetic_series(days=60)
    data = build_report(
        portfolio_name="Short window",
        positions={"AAPL": 1000.0},
        period="1mo",
        cum_return=0.02,
        health_score=50,
        metric_rows=METRIC_ROWS[:3],
        insights=[],
        suggestions=[],
        pf_value=short_value,
    )
    with pdfplumber.open(BytesIO(data)) as pdf:
        assert len(pdf.pages) == 3
        page3 = pdf.pages[2].extract_text()
    assert "CAUTION" in page3
    assert "shorter than one year" in page3


def test_report_without_optional_data_still_three_pages():
    data = build_report(
        portfolio_name="Bare portfolio",
        positions={"AAPL": 1000.0},
        period="1y",
        cum_return=0.05,
        health_score=50,
        metric_rows=METRIC_ROWS[:3],
        insights=[],
        suggestions=[],
    )
    with pdfplumber.open(BytesIO(data)) as pdf:
        assert len(pdf.pages) == 3


def test_report_aggregates_positions_beyond_twelve():
    positions = {f"T{i:02d}": 1000.0 - i for i in range(16)}
    data = build_report(
        portfolio_name="Wide portfolio",
        positions=positions,
        period="1y",
        cum_return=0.0,
        health_score=50,
        metric_rows=METRIC_ROWS,
        insights=[],
        suggestions=[],
    )
    with pdfplumber.open(BytesIO(data)) as pdf:
        assert len(pdf.pages) == 3
        page1 = pdf.pages[0].extract_text()
    assert "+4" in page1 and "other holdings" in page1
