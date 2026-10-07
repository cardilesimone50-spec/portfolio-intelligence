"""Panoramica cliente Advisor: controlli di monitoraggio, indicatori, posizioni (senza rete)."""

import numpy as np
import pandas as pd
import pytest

from portfolio_intelligence.analytics.pipeline import analyze_portfolio
from portfolio_intelligence.fundamentals.valuation import empty_fundamentals
from portfolio_intelligence.i18n import set_language
from portfolio_intelligence.views import advisor_overview as ov
from portfolio_intelligence.views.context import ViewContext


@pytest.fixture(autouse=True)
def _english():
    set_language("en")
    yield
    set_language("en")


def _prices(tickers, days=300, seed=7):
    rng = np.random.default_rng(seed)
    index = pd.bdate_range("2024-01-01", periods=days)
    data = {
        ticker: 100 * np.cumprod(1 + rng.normal(0.0005, 0.01 * (i + 1), days))
        for i, ticker in enumerate(tickers)
    }
    return pd.DataFrame(data, index=index)


def _ctx(weights: dict[str, float], profile="Moderate", sectors=None) -> ViewContext:
    tickers = list(weights)
    prices = _prices(tickers)
    bench = _prices(["QQQ"], seed=11)
    fund = empty_fundamentals(tickers)
    if sectors:
        fund["sector"] = pd.Series(sectors)
    portfolio = [{"ticker": k, "weight": v} for k, v in weights.items()]
    computed = analyze_portfolio(prices, bench, portfolio, fund)
    total = 100_000.0
    pos = pd.DataFrame(
        {
            "qty": {k: 10.0 for k in tickers},
            "buy_price": {k: 90.0 for k in tickers},
            "current_price": {k: float(prices[k].iloc[-1]) for k in tickers},
            "pnl": {k: 100.0 for k in tickers},
            "pnl_pct": {k: 0.1 for k in tickers},
        }
    )
    return ViewContext(
        computed=computed,
        amounts={k: total * w for k, w in weights.items()},
        total=total,
        portfolio=portfolio,
        portfolio_name="C-1",
        period="1y",
        in_eur=True,
        risk_free=0.03,
        risk_profile=profile,
        advisor="adv@x",
        names={k: f"{k} Inc." for k in tickers},
        pos=pos,
        pnl_totals={"value": total, "cost": 90_000.0, "pnl": 10_000.0, "pnl_pct": 0.111},
        irr=0.08,
    )


def _check(checks, key):
    return next(c for c in checks if c["key"] == key)


def test_concentrated_portfolio_breaches_the_position_threshold():
    checks = ov.monitoring_checks(_ctx({"AAA": 0.7, "BBB": 0.2, "CCC": 0.1}))
    largest = _check(checks, "max_position")
    assert largest["status"] == ov.BREACH
    assert largest["measured"] == "AAA 70%"


def test_balanced_portfolio_stays_within_the_position_threshold():
    checks = ov.monitoring_checks(_ctx({f"T{i}": 0.2 for i in range(5)}))
    assert _check(checks, "max_position")["status"] == ov.OK


def test_undeclared_profile_is_not_assumed():
    """Nessun limite presunto: senza profilo dichiarato il controllo resta non applicabile."""
    checks = ov.monitoring_checks(_ctx({"AAA": 0.5, "BBB": 0.5}, profile="Not set"))
    vol = _check(checks, "profile_vol")
    assert vol["status"] == ov.NA
    assert vol["limit"] == "Profile not declared"


def test_profile_threshold_matches_the_declared_profile():
    conservative = _check(
        ov.monitoring_checks(_ctx({"AAA": 0.5, "BBB": 0.5}, "Conservative")), "profile_vol"
    )
    aggressive = _check(
        ov.monitoring_checks(_ctx({"AAA": 0.5, "BBB": 0.5}, "Aggressive")), "profile_vol"
    )
    assert conservative["limit"] == "≤ 10%"
    assert aggressive["limit"] == "≤ 30%"


def test_single_position_skips_pairwise_checks():
    keys = {c["key"] for c in ov.monitoring_checks(_ctx({"AAA": 1.0}))}
    assert "risk_share" not in keys and "correlation" not in keys
    assert {"profile_vol", "max_position", "usd", "drawdown", "health"} <= keys


def test_key_figures_show_pnl_and_benchmark_side_by_side():
    cells = {
        label: (value, sub)
        for label, value, sub, _ in ov.key_figures(_ctx({"AAA": 0.5, "BBB": 0.5}))
    }
    assert cells["Market value"][0] == "€100,000"
    assert cells["Unrealized P&L"][0] == "+€10,000"
    assert "QQQ" in cells["Return 1 year"][1]
    assert cells["Money-weighted return"][0] == "+8.0%"


def test_key_figures_follow_the_interface_language():
    set_language("it")
    cells = {label: value for label, value, _, _ in ov.key_figures(_ctx({"AAA": 0.5, "BBB": 0.5}))}
    assert cells["Valore di mercato"] == "100.000 €"
    assert cells["Rendimento money-weighted"] == "+8,0%"


def test_unknown_cost_basis_is_not_shown_as_a_number():
    ctx = _ctx({"AAA": 0.5, "BBB": 0.5})
    ctx.pnl_totals = {"value": 1.0, "cost": 1.0, "pnl": float("nan"), "pnl_pct": float("nan")}
    cells = {label: (value, sub) for label, value, sub, _ in ov.key_figures(ctx)}
    assert cells["Unrealized P&L"] == ("n/a", "Cost basis not available")


def test_holdings_are_sorted_by_value_with_weights_summing_to_one():
    frame = ov.holdings_frame(_ctx({"AAA": 0.2, "BBB": 0.5, "CCC": 0.3}))
    assert list(frame["ticker"]) == ["BBB", "CCC", "AAA"]
    assert frame["weight"].sum() == pytest.approx(1.0)
    assert frame["risk"].sum() == pytest.approx(1.0, abs=1e-6)
    assert frame.loc[0, "name"] == "BBB Inc."


def test_sector_weights_group_unclassified_holdings():
    ctx = _ctx(
        {"AAA": 0.5, "BBB": 0.3, "CCC": 0.2}, sectors={"AAA": "Technology", "BBB": "Technology"}
    )
    weights = ov.sector_weights(ctx)
    assert weights["Technology"] == pytest.approx(0.8)
    assert weights.sum() == pytest.approx(1.0)
    assert len(weights) == 2


def _overview_app(ctx):
    from portfolio_intelligence.views import advisor_overview

    advisor_overview.render(ctx, lambda: "")


def test_overview_renders_without_errors(tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'ov.db'}")
    ctx = _ctx({"AAA": 0.6, "BBB": 0.4})
    at = AppTest.from_function(_overview_app, args=(ctx,), default_timeout=30).run()

    assert not at.exception
    page = " ".join(m.value for m in at.markdown)
    assert "Monitoring checks" in page or "MONITORING CHECKS" in page.upper()
    assert any(b.label == "Export CSV" for b in at.get("download_button"))


def test_both_reports_build_from_a_client_context(tmp_path, monkeypatch):
    """Dal contesto della scheda cliente ai due PDF, come al clic sui pulsanti."""
    from io import BytesIO

    import pdfplumber

    from portfolio_intelligence.views import checkup
    from portfolio_intelligence.visualization.pdf_advisor import build_advisor_report
    from portfolio_intelligence.visualization.pdf_report import build_investor_report

    monkeypatch.setattr(checkup, "report_projection", lambda ctx: None)
    ctx = _ctx({"AAA": 0.6, "BBB": 0.4})
    ctx.report_recipient = "Mario Rossi"
    report = checkup.report_input(
        ctx,
        checkup.executive_text(ctx),
        checkup.top_problems(ctx),
        [],
        monitoring=ov.monitoring_checks(ctx),
    )
    assert report.advisor_issued and report.recipient == "Mario Rossi"
    assert report.profile_band == 0.18  # profilo Moderate dichiarato
    with pdfplumber.open(BytesIO(build_advisor_report(report))) as pdf:
        text = " ".join(page.extract_text() for page in pdf.pages)
    assert "8. SUITABILITY CONTEXT" in text and "Largest position" in text
    with pdfplumber.open(BytesIO(build_investor_report(report))) as pdf:
        assert len(pdf.pages) == 4
        assert "Prepared for Mario Rossi" in pdf.pages[0].extract_text()
