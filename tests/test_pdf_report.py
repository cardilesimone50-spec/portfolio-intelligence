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
    assert "Suitability check" in page1
    assert "Data coverage" in page1
    assert "Sharpe ratio" in page2
    assert "Expected shortfall" in page2
    assert "HEALTH SCORE" in page2.upper()
    assert "ALLOCATION BY SECTOR" in page3
    assert "Technology" in page3
    assert "STRESS SCENARIO" in page3
    assert "METHODOLOGY" in page3
    assert "RECOMMENDATIONS" in page3
    # il markdown ** non deve finire nel PDF
    assert "**" not in page3


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
