"""Report PDF: Investor di quattro pagine, Advisor come revisione di portafoglio.

Gli stessi numeri nelle due versioni; cambia la profondità. Nessuna rete:
i dati sono sintetici (tests/conftest.py).
"""

from io import BytesIO

import pdfplumber
import pytest

from portfolio_intelligence.analytics.monte_carlo import scenario_table, simulate
from portfolio_intelligence.visualization.pdf_advisor import build_advisor_report
from portfolio_intelligence.visualization.pdf_report import build_investor_report

CONSUMER_PHRASES = ("good sign", "bad day", "test your discipline", "how to read", "well paid")


def _pages(data: bytes) -> list[str]:
    assert data.startswith(b"%PDF")
    with pdfplumber.open(BytesIO(data)) as pdf:
        return [page.extract_text() or "" for page in pdf.pages]


def _text(pages: list[str]) -> str:
    return " ".join(pages).replace("\n", " ")


def _projection(total: float = 16_000.0) -> dict:
    from conftest import WEIGHTS, synthetic_market

    prices, _ = synthetic_market()
    result = simulate(
        total, WEIGHTS, prices.pct_change().dropna(), horizon_years=5, n_simulations=200
    )
    return {
        "rows": scenario_table(result),
        "paths": result.paths,
        "cagr": {f"p{p}": result.cagr(p) for p in (10, 50, 90)},
        "prob_loss": result.prob_loss,
        "method": result.method,
        "n": result.n_simulations,
        "horizon": result.horizon_years,
    }


# ------------------------------------------------------------------ Investor


def test_investor_report_has_four_pages_with_the_required_sections(make_report):
    pages = _pages(build_investor_report(make_report()))
    assert len(pages) == 4
    p1, p2, p3, p4 = pages
    assert "PORTFOLIO OVERVIEW" in p1
    for label in (
        "CURRENT VALUE",
        "INVESTED CAPITAL",
        "CAGR",
        "SHARPE RATIO",
        "SORTINO RATIO",
        "EXPECTED SHORTFALL",
        "CONCENTRATION",
        "RELATIVE PERFORMANCE",
    ):
        assert label in p1, label
    assert "PORTFOLIO HEALTH SCORE" in p1 and "Proprietary composite indicator" in p1
    assert "Risk profile check" in p1 and "MiFID II suitability" in p1
    for block in (
        "ABSOLUTE PERFORMANCE",
        "BENCHMARK-RELATIVE PERFORMANCE",
        "RISK-ADJUSTED PERFORMANCE",
    ):
        assert block in p2, block
    assert "DRAWDOWN AND RECOVERY" in p2
    assert "CAPITAL WEIGHT AND RISK CONTRIBUTION" in p3
    assert "Risk/weight" in p3
    for category in (
        "Market risk",
        "Concentration risk",
        "Currency risk",
        "Liquidity risk",
        "Valuation risk",
    ):
        assert category in p3, category
    assert "STRESS TESTING" in p4 and "Correlation-adjusted" in p4
    assert "HISTORICAL 12-MONTH OUTCOMES" in p4
    assert "Bear (5th percentile)" in p4 and "not a forecast" in _text([p4])
    assert "METHODOLOGY" in p4
    for page in pages:
        assert "Past performance is not a reliable indicator" in page
        assert "of 4" in page


def test_investor_report_never_projects_without_an_advisor(make_report):
    """La landing Investor promette nessuna previsione: niente Monte Carlo nel suo PDF."""
    text = _text(_pages(build_investor_report(make_report())))
    assert "MONTE CARLO" not in text.upper()
    assert "personal information of the portfolio holder" in text


def test_client_copy_issued_by_the_advisor_includes_the_projection_with_its_method(make_report):
    report = make_report(projection=_projection(), advisor_issued=True, recipient="Mario Rossi")
    pages = _pages(build_investor_report(report))
    assert len(pages) == 4
    text = _text(pages)
    assert "Prepared for Mario Rossi" in pages[0]
    assert "PROBABILISTIC PROJECTION (MONTE CARLO)" in text
    assert "200 simulations" in text and "constant current weights" in text
    assert "not a forecast or a guarantee" in text
    assert "Prepared exclusively for the named recipient" in text


def test_investor_report_uses_institutional_language(make_report):
    text = _text(_pages(build_investor_report(make_report()))).lower()
    for phrase in CONSUMER_PHRASES:
        assert phrase not in text, phrase
    assert "**" not in text


def test_investor_report_formats_numbers_in_the_document_language(make_report):
    en = _text(_pages(build_investor_report(make_report())))
    it = _text(_pages(build_investor_report(make_report(lang="it"))))
    assert "€16,000" in en
    assert "16.000 €" in it
    assert "PANORAMICA DEL PORTAFOGLIO" in it
    assert "I rendimenti passati non sono un indicatore affidabile" in it
    assert "Pagina 1 di 4" in it


def test_investor_report_without_cost_basis_shows_no_invented_pnl(make_report):
    pages = _pages(build_investor_report(make_report(invested=None, pnl=None, pnl_pct=None)))
    assert "Cost basis not available" in pages[0]


def test_short_window_report_states_its_limits(make_report):
    report = make_report(days=180)
    text = _text(_pages(build_investor_report(report)))
    assert "shorter than one year" in text
    assert "Fewer than 13 months of history" in text


def test_investor_report_aggregates_positions_beyond_twelve(make_report):
    report = make_report()
    report.positions = {f"T{i:02d}": 1000.0 - i for i in range(16)}
    pages = _pages(build_investor_report(report))
    assert len(pages) == 4
    assert "+4" in pages[2] and "other holdings" in pages[2]


# ------------------------------------------------------------------ Advisor


def test_advisor_report_follows_the_portfolio_review_structure(make_report):
    report = make_report(
        projection=_projection(),
        advisor_issued=True,
        advisor="advisor@example.com",
        monitoring=[
            {
                "label": "Largest position",
                "measured": "NVDA 40%",
                "limit": "≤ 25%",
                "status": "breach",
            }
        ],
    )
    pages = _pages(build_advisor_report(report))
    assert len(pages) >= 5
    text = _text(pages)
    sections = [
        "1. EXECUTIVE INVESTMENT VIEW",
        "2. PORTFOLIO PROFILE",
        "3. PERFORMANCE ANALYSIS",
        "4. COMPOSITION AND CONCENTRATION",
        "5. RISK ANALYSIS",
        "6. STRESS TESTING",
        "7. SCENARIO ANALYSIS",
        "8. SUITABILITY CONTEXT",
        "9. COMPOSITE SCORE AND RULE-BASED OBSERVATIONS",
        "10. REVIEW CONSIDERATIONS",
        "11. METHODOLOGY, DATA SOURCES AND DISCLOSURES",
    ]
    positions = [text.find(title) for title in sections]
    assert all(pos >= 0 for pos in positions), dict(zip(sections, positions, strict=True))
    assert positions == sorted(positions)  # nell'ordine della revisione
    for heading in (
        "PORTFOLIO POSITIONING",
        "RISK REGIME",
        "KEY VULNERABILITIES",
        "KEY STRENGTHS",
        "MATERIAL INVESTMENT IMPLICATIONS",
    ):
        assert heading in text, heading
    for metric in ("Tracking error", "Information ratio", "Up / down capture", "Assessment"):
        assert metric in text, metric
    for field in (
        "Number of simulations",
        "Historical period",
        "Current weights held constant",
        "Statistical scenario derived from history; not a forecast",
    ):
        assert field in text, field
    assert "LARGEST DRAWDOWN EPISODES" in text
    assert "does not replace, the MiFID II suitability assessment" in text
    assert f"of {len(pages)}" in pages[-1]


def test_advisor_and_investor_reports_show_the_same_numbers(make_report):
    report = make_report(projection=_projection(), advisor_issued=True)
    investor = _text(_pages(build_investor_report(report)))
    advisor = _text(_pages(build_advisor_report(report)))
    m = report.metrics
    for value in (
        report.pct(m.cagr, signed=True),
        report.pct(m.vol),
        report.pct(m.max_dd),
        report.pct(m.es95),
    ):
        assert value in investor and value in advisor, value


def test_advisor_report_without_projection_says_so(make_report):
    text = _text(_pages(build_advisor_report(make_report())))
    assert "Monte Carlo projection not available" in text


def test_advisor_report_in_italian(make_report):
    pages = _pages(build_advisor_report(make_report(lang="it", projection=_projection())))
    text = _text(pages)
    assert "1. SINTESI D'INVESTIMENTO" in text
    assert "Valutazione" in text
    assert "Scenario statistico ricavato dallo storico" in text
    assert "Pagina 1 di" in pages[0]


@pytest.mark.parametrize("builder", [build_investor_report, build_advisor_report])
def test_reports_survive_a_single_position_portfolio(make_report, builder):
    report = make_report()
    report.positions = {"NVDA": 10_000.0}
    assert len(_pages(builder(report))) >= 1
