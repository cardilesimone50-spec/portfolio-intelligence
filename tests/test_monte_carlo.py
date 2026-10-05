"""Simulazione Monte Carlo: determinismo, percentili, casi limite, grafico e PDF."""

from io import BytesIO

import numpy as np
import pandas as pd
import pdfplumber
import pytest

from portfolio_intelligence.analytics.monte_carlo import (
    METHODS,
    PERCENTILES,
    MonteCarloResult,
    scenario_table,
    simulate,
)

rng = np.random.default_rng(7)
DAYS = pd.bdate_range("2023-01-02", periods=500)
RETURNS = pd.DataFrame(
    {
        "AAA": rng.normal(0.0006, 0.012, len(DAYS)),
        "BBB": rng.normal(0.0003, 0.020, len(DAYS)),
        "CCC": rng.standard_t(3, len(DAYS)) * 0.01,  # code grasse
    },
    index=DAYS,
)
WEIGHTS = {"AAA": 0.5, "BBB": 0.3, "CCC": 0.2}


def _run(**kwargs) -> MonteCarloResult:
    params = {
        "initial_value": 10_000.0,
        "weights": WEIGHTS,
        "historical_returns": RETURNS,
        "horizon_years": 3,
        "n_simulations": 500,
    }
    params.update(kwargs)
    return simulate(**params)


# ------------------------------------------------------------------ proprietà di base


@pytest.mark.parametrize("method", METHODS)
def test_same_seed_gives_identical_results(method):
    a = _run(method=method, random_state=123)
    b = _run(method=method, random_state=123)
    pd.testing.assert_frame_equal(a.paths, b.paths)
    np.testing.assert_array_equal(a.final_values, b.final_values)


@pytest.mark.parametrize("method", METHODS)
def test_different_seeds_give_different_results(method):
    assert not np.array_equal(
        _run(method=method, random_state=1).final_values,
        _run(method=method, random_state=2).final_values,
    )


@pytest.mark.parametrize("method", METHODS)
def test_percentiles_are_ordered_at_every_point_in_time(method):
    paths = _run(method=method, horizon_years=5).paths
    columns = [f"p{p}" for p in PERCENTILES]
    assert (paths[columns].diff(axis=1).iloc[:, 1:] >= -1e-9).all().all()


@pytest.mark.parametrize("method", METHODS)
def test_all_percentiles_start_at_the_initial_value(method):
    result = _run(method=method, initial_value=12_345.0)
    assert result.paths.index[0] == 0.0
    assert (result.paths.iloc[0] == 12_345.0).all()


@pytest.mark.parametrize("horizon", [1, 3, 5])
def test_one_point_per_month_up_to_the_horizon(horizon):
    paths = _run(horizon_years=horizon).paths
    assert len(paths) == 12 * horizon + 1
    assert paths.index[-1] == pytest.approx(horizon)


def test_summary_metrics_are_consistent():
    result = _run(n_simulations=2000)
    assert 0.0 <= result.prob_loss <= 1.0
    assert result.prob_gain == pytest.approx(1 - result.prob_loss)
    assert result.median_final == pytest.approx(np.percentile(result.final_values, 50))
    assert result.var_95 == pytest.approx(10_000.0 - np.percentile(result.final_values, 5))
    assert result.worst_case["p5"] <= result.worst_case["p10"] <= result.median_final
    assert result.median_final <= result.best_case["p90"] <= result.best_case["p95"]
    cagr = result.cagr_by_percentile
    assert cagr["p50"] == pytest.approx((result.median_final / 10_000.0) ** (1 / 3) - 1)
    assert list(cagr) == [f"p{p}" for p in PERCENTILES]
    assert sorted(cagr.values()) == list(cagr.values())


# ------------------------------------------------------------------ correttezza dei metodi


def test_bootstrap_of_a_constant_return_compounds_exactly():
    flat = pd.DataFrame({"AAA": [0.001] * 60}, index=pd.bdate_range("2024-01-01", periods=60))
    result = simulate(1000.0, {"AAA": 1.0}, flat, horizon_years=1, n_simulations=50)
    expected = 1000.0 * 1.001**252
    assert result.final_values == pytest.approx(np.full(50, expected))


def test_gbm_median_tracks_the_historical_geometric_growth():
    result = _run(method="gbm", n_simulations=5000, horizon_years=5)
    daily = RETURNS.to_numpy() @ np.array([0.5, 0.3, 0.2])
    expected = 10_000.0 * np.exp(np.log1p(daily).mean() * 252 * 5)
    assert result.median_final == pytest.approx(expected, rel=0.03)


def test_bootstrap_only_draws_historical_portfolio_days():
    result = _run(horizon_years=1, n_simulations=200)
    daily = RETURNS.to_numpy() @ np.array([0.5, 0.3, 0.2])
    worst_month_bound = 10_000.0 * (1 + daily.min()) ** 21
    assert result.paths["p5"].iloc[1] >= worst_month_bound - 1e-6


# ------------------------------------------------------------------ casi limite


def test_single_asset_portfolio():
    result = simulate(5000.0, {"AAA": 1.0}, RETURNS[["AAA"]], n_simulations=200)
    assert (result.paths.iloc[0] == 5000.0).all()
    assert result.final_values.shape == (200,)


@pytest.mark.parametrize("method", METHODS)
def test_unnormalised_weights_equal_their_normalised_version(method):
    raw = _run(method=method, weights={"AAA": 5, "BBB": 3, "CCC": 2})
    normalised = _run(method=method, weights=WEIGHTS)
    pd.testing.assert_frame_equal(raw.paths, normalised.paths)


def test_array_weights_follow_column_order():
    by_name = _run(weights=WEIGHTS)
    by_array = _run(weights=np.array([0.5, 0.3, 0.2]))
    pd.testing.assert_frame_equal(by_name.paths, by_array.paths)


def test_zero_weight_assets_are_ignored_even_with_missing_history():
    returns = RETURNS.copy()
    returns.loc[returns.index[:300], "CCC"] = np.nan  # CCC a peso zero: non accorcia lo storico
    result = simulate(1000.0, {"AAA": 1.0, "BBB": 1.0, "CCC": 0.0}, returns, n_simulations=100)
    assert result.final_values.shape == (100,)


@pytest.mark.parametrize(
    "weights",
    [{"AAA": 0.0, "BBB": 0.0}, np.zeros(3), {"AAA": -0.5, "BBB": 1.5}],
)
def test_null_or_negative_weights_are_rejected(weights):
    with pytest.raises(ValueError):
        _run(weights=weights)


def test_weights_for_unknown_tickers_are_rejected():
    with pytest.raises(ValueError, match="ZZZ"):
        _run(weights={"AAA": 0.5, "ZZZ": 0.5})


def test_short_history_is_rejected_but_a_short_valid_one_works():
    with pytest.raises(ValueError, match="joint history"):
        simulate(1000.0, {"AAA": 1.0}, RETURNS[["AAA"]].iloc[:10], n_simulations=50)
    ok = simulate(1000.0, {"AAA": 1.0}, RETURNS[["AAA"]].iloc[:25], n_simulations=50)
    assert ok.final_values.shape == (50,)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"initial_value": 0.0},
        {"horizon_years": 0},
        {"horizon_years": 6},
        {"n_simulations": 5},
        {"method": "magic"},
    ],
)
def test_invalid_parameters_are_rejected(kwargs):
    with pytest.raises(ValueError):
        _run(**kwargs)


def test_scenario_table_reads_1_3_5_years_and_skips_beyond_horizon():
    long = _run(horizon_years=5)
    table = scenario_table(long)
    assert [row["years"] for row in table] == [1, 3, 5]
    assert all(row["initial"] == 10_000.0 for row in table)
    assert table[-1]["p50"] == pytest.approx(long.median_final)
    assert all(row["p10"] <= row["p50"] <= row["p90"] for row in table)
    assert [row["years"] for row in scenario_table(_run(horizon_years=3))] == [1, 3]


# ------------------------------------------------------------------ grafico, PDF, confini


def test_fan_chart_has_bands_median_baseline_and_euro_axis():
    from portfolio_intelligence.visualization.monte_carlo_charts import fan_chart, fan_data

    result = _run()
    spec = fan_chart(result).to_dict()
    marks = [layer["mark"]["type"] for layer in spec["layer"]]
    assert marks.count("area") == 2 and "line" in marks and marks.count("rule") == 2
    assert "€" in spec["layer"][0]["encoding"]["y"]["axis"]["labelExpr"]
    data = fan_data(result)
    assert data["p50_eur"].iloc[0] == "10.000 €"  # punto come separatore delle migliaia


def test_client_report_projection_percentages_use_the_simulated_initial_value(make_report):
    from portfolio_intelligence.visualization.pdf_report import build_investor_report

    result = _run(horizon_years=5)
    projection = {
        "rows": scenario_table(result),
        "paths": result.paths,
        "cagr": {f"p{p}": result.cagr(p) for p in (10, 50, 90)},
        "prob_loss": result.prob_loss,
        "method": result.method,
        "n": result.n_simulations,
        "horizon": result.horizon_years,
    }
    report = make_report(projection=projection, advisor_issued=True)
    with pdfplumber.open(BytesIO(build_investor_report(report))) as pdf:
        assert len(pdf.pages) == 4
        page4 = pdf.pages[3].extract_text()
    assert (
        "Bear scenario (10th percentile)" in page4 and "Bull scenario (90th percentile)" in page4
    )
    # percentuali sul valore iniziale simulato, non sul totale del portafoglio nel PDF
    p10_1y = projection["rows"][0]["p10"]
    assert f"({p10_1y / 10_000.0 - 1:+.0%})" in page4


def test_investor_area_never_shows_projections():
    """La landing Investor dichiara "nessuna previsione di rendimento"."""
    with open("app_investor.py") as f:
        assert "monte_carlo" not in f.read()
    with open("portfolio_intelligence/views/checkup.py") as f:
        source = f.read()
    assert "projection=report_projection(ctx) if ctx.stateful else None" in source
    with open("portfolio_intelligence/visualization/pdf_report.py") as f:
        assert "simulate(" not in f.read()  # il PDF Investor non calcola proiezioni da sé


def test_report_projection_uses_the_client_portfolio_and_value():
    from portfolio_intelligence.views.context import ViewContext
    from portfolio_intelligence.views.monte_carlo import report_projection

    ctx = ViewContext(
        computed={"returns": RETURNS},
        amounts={"AAA": 6000.0, "BBB": 4000.0},
        total=10_000.0,
        portfolio=[{"ticker": "AAA", "weight": 0.6}, {"ticker": "BBB", "weight": 0.4}],
        portfolio_name="C-1",
        period="2y",
        in_eur=True,
        risk_free=0.03,
        risk_profile="Moderate",
        advisor="adv@x",
    )
    projection = report_projection(ctx)
    assert projection is not None
    rows = projection["rows"]
    assert [row["years"] for row in rows] == [1, 3, 5]
    assert all(row["initial"] == 10_000.0 for row in rows)
    assert projection["n"] == 1000 and projection["method"] == "bootstrap"
    assert projection["paths"].index[-1] == 5.0
    assert 0.0 <= projection["prob_loss"] <= 1.0
    assert report_projection(ViewContext(None, {}, 0.0, [], "", "1y", True, 0.03, "", "")) is None
