"""Fixture condivise: dati di report sintetici e deterministici (nessuna rete)."""

import numpy as np
import pandas as pd
import pytest

from portfolio_intelligence.analytics.insights import monthly_returns
from portfolio_intelligence.analytics.pipeline import analyze_portfolio
from portfolio_intelligence.analytics.report_metrics import compute_report_metrics, stress_tests
from portfolio_intelligence.fundamentals.valuation import empty_fundamentals
from portfolio_intelligence.visualization.pdf_common import ReportInput

TICKERS = ["NVDA", "AAPL", "MSFT"]
WEIGHTS = {"NVDA": 0.4, "AAPL": 0.37, "MSFT": 0.23}


def synthetic_market(days: int = 1250, seed: int = 7) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Prezzi di tre titoli legati a un fattore di mercato e del benchmark QQQ."""
    rng = np.random.default_rng(seed)
    index = pd.bdate_range("2021-10-01", periods=days)
    market = rng.normal(0.0005, 0.011, days)
    prices = pd.DataFrame(
        {
            ticker: 100
            * np.cumprod(1 + market * (1.0 + 0.3 * i) + rng.normal(0.0003, 0.008 * (i + 1), days))
            for i, ticker in enumerate(TICKERS)
        },
        index=index,
    )
    bench = pd.DataFrame({"QQQ": 100 * np.cumprod(1 + market)}, index=index)
    return prices, bench


def build_report_input(days: int = 1250, **overrides) -> ReportInput:
    prices, bench = synthetic_market(days)
    fund = empty_fundamentals(TICKERS)
    fund["sector"] = pd.Series({ticker: "Technology" for ticker in TICKERS})
    fund["pe"] = pd.Series({"NVDA": 55.0, "AAPL": 32.0, "MSFT": 35.0})
    portfolio = [{"ticker": k, "weight": v} for k, v in WEIGHTS.items()]
    computed = analyze_portfolio(prices, bench, portfolio, fund)
    weights = pd.Series(WEIGHTS)
    metrics = compute_report_metrics(
        computed["pf_daily"],
        computed["bench_daily"],
        weights,
        computed["contributions"],
        fund,
        computed["usd_weight"],
        risk_free=0.04,
    )
    total = 16_000.0
    fields = dict(
        portfolio_name="C-0042",
        positions={k: total * v for k, v in WEIGHTS.items()},
        period="5y" if days > 600 else "1y",
        metrics=metrics,
        pf_value=computed["pf_value"],
        bench_value=(1 + computed["bench_daily"]).cumprod(),
        health=computed["health"],
        breakdown=computed["breakdown"],
        executive="Over the period the portfolio returned **+12.3%**.",
        names={"NVDA": "NVIDIA Corp.", "AAPL": "Apple Inc.", "MSFT": "Microsoft Corp."},
        sector_of={ticker: "Technology" for ticker in TICKERS},
        monthly=monthly_returns(computed["pf_daily"]),
        bench_monthly=monthly_returns(computed["bench_daily"]),
        per_ticker_returns=prices.iloc[-1] / prices.iloc[0] - 1,
        per_ticker_pnl=pd.Series({"NVDA": 4700.0, "AAPL": 3200.0, "MSFT": 1400.0}),
        observations=["**NVDA** is **40%** of the portfolio: high concentration risk."],
        what_if=["Halve NVDA (redistributing to the others): lower annual swing."],
        stress=stress_tests(computed["returns"], weights, metrics, include_fx=True),
        risk_profile="Moderate",
        profile_band=0.18,
        risk_free=0.04,
        invested=8000.0,
        pnl=8000.0,
        pnl_pct=1.0,
        price_source="Yahoo (chart)",
    )
    fields.update(overrides)
    return ReportInput(**fields)


@pytest.fixture
def make_report():
    """Costruttore di ReportInput sintetici: make_report(lang="it", recipient=...)."""
    return build_report_input


@pytest.fixture
def returns_frame():
    prices, _ = synthetic_market()
    return prices.pct_change().dropna()
