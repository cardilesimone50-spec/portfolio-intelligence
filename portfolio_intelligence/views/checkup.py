"""Vista Check-up: hero, executive summary, problemi, rischio in euro, PDF."""

import pandas as pd
import streamlit as st

from portfolio_intelligence.analytics.alerts import evaluate_alerts
from portfolio_intelligence.analytics.insights import (
    dna_label,
    dna_scores,
    equal_weight_portfolio,
    executive_summary,
    find_opportunities,
    find_problems,
    health_breakdown,
    monthly_returns,
    portfolio_health_score,
    radar_scores,
    reduce_position,
    usd_exposure,
)
from portfolio_intelligence.analytics.interpret import (
    interpret_volatility,
)
from portfolio_intelligence.analytics.performance import (
    max_drawdown,
)
from portfolio_intelligence.analytics.report_metrics import compute_report_metrics, stress_tests
from portfolio_intelligence.data import yahoo_client
from portfolio_intelligence.data.store import load_analyses, log_analysis, log_audit
from portfolio_intelligence.i18n import t, t_in
from portfolio_intelligence.portfolio.returns import (
    compute_daily_returns,
    per_ticker_cumulative_return,
    portfolio_daily_returns,
)
from portfolio_intelligence.portfolio.risk import portfolio_volatility
from portfolio_intelligence.ui.components import breakdown_html, eur, hero_html, kpi_row_html, sec
from portfolio_intelligence.ui.identity import DEV_ADVISOR
from portfolio_intelligence.views.common import (
    BENCHMARK,
    PROFILE_VOL,
    TRADING_DAYS,
    load_market_db,
)
from portfolio_intelligence.views.context import ViewContext
from portfolio_intelligence.views.monte_carlo import report_projection
from portfolio_intelligence.visualization.charts import equity_area, simple_line
from portfolio_intelligence.visualization.pdf_advisor import build_advisor_report
from portfolio_intelligence.visualization.pdf_common import ReportInput
from portfolio_intelligence.visualization.pdf_report import build_investor_report


def render(ctx: ViewContext) -> None:
    # garantito da app.py: questa vista è dispatchata solo con un portafoglio
    # calcolato (NEEDS_PORTFOLIO); l'assert documenta l'invariante e lascia
    # mypy restringere il tipo da qui in poi.
    assert ctx.computed is not None
    c = ctx.computed
    amounts, total, portfolio = ctx.amounts, ctx.total, ctx.portfolio
    period = ctx.period

    pnl_totals = ctx.pnl_totals or {}
    col_hero, col_equity = st.columns([1, 1.4], gap="large")
    with col_hero:
        st.markdown(
            hero_html(
                c["health"],
                eur(total),  # valore attuale reale: Σ quantità × ultimo prezzo
                c["cum_return"],
                period,
                today_move=float(c["pf_daily"].iloc[-1]),
                gain=pnl_totals.get("pnl"),
                gain_pct=pnl_totals.get("pnl_pct"),
                irr=ctx.irr,
            ),
            unsafe_allow_html=True,
        )
        st.caption(t("chk.health_caption"))
        if c["dna"]:
            st.markdown(f"**{dna_label(c['dna'])}**")
    with col_equity:
        sec(t("chk.capital_section", period=period))
        st.altair_chart(
            equity_area(total * (1 + c["pf_daily"]).cumprod(), total),
            width="stretch",
        )
        st.caption(t("chk.capital_caption"))

    col_break, col_exec = st.columns([1, 1.4], gap="large")
    with col_break:
        st.markdown(breakdown_html(c["breakdown"]), unsafe_allow_html=True)
    with col_exec:
        sec(t("chk.exec_section"))
        exec_text = executive_text(ctx)
        st.markdown(exec_text)
        st.caption(t("chk.exec_caption"))

    sec(t("chk.holdings"))
    cum_by_ticker = per_ticker_cumulative_return(c["prices"])
    normalized_pos = c["prices"] / c["prices"].apply(lambda s: s.dropna().iloc[0])
    fund_names = c["fund"]["name"] if "name" in c["fund"].columns else pd.Series(dtype=str)
    pos = ctx.pos if ctx.pos is not None else pd.DataFrame()
    position_rows = [
        {
            "Ticker": ticker,
            "Company": fund_names.get(ticker, ""),
            "Qty": float(pos["qty"].get(ticker)) if len(pos) else None,
            "Buy": float(pos["buy_price"].get(ticker)) if len(pos) else None,
            "Date": (
                pos["buy_date"].get(ticker).date()
                if len(pos) and pd.notna(pos["buy_date"].get(ticker))
                else None
            ),
            "Current": float(pos["current_price"].get(ticker)) if len(pos) else None,
            "Value": amounts[ticker],
            "PnL": float(pos["pnl"].get(ticker)) if len(pos) else None,
            "PnLPct": float(pos["pnl_pct"].get(ticker)) if len(pos) else None,
            "Ann": float(pos["ann_pct"].get(ticker)) if len(pos) else None,
            "Weight": amounts[ticker] / total,
            "Return": cum_by_ticker.get(ticker),
            "Trend": normalized_pos[ticker].dropna().tolist()[-130:],
        }
        for ticker in sorted(amounts, key=lambda t: amounts[t], reverse=True)
    ]
    positions_df = pd.DataFrame(position_rows)

    def _pnl_color(value) -> str:
        if value is None or value != value:
            return ""
        return (
            "color: #0ea371; font-weight: 600"
            if value >= 0
            else "color: #dc2626; font-weight: 600"
        )

    st.dataframe(
        positions_df.style.map(_pnl_color, subset=["PnL", "PnLPct", "Ann"]),
        column_config={
            "Ticker": st.column_config.TextColumn(t("chk.col_ticker")),
            "Company": st.column_config.TextColumn(t("chk.col_company")),
            "Qty": st.column_config.NumberColumn(t("pos.qty"), format="%.4g"),
            "Buy": st.column_config.NumberColumn(t("pos.buy_price"), format="%.2f"),
            "Date": st.column_config.DateColumn(t("pos.buy_date"), format="DD/MM/YYYY"),
            "Current": st.column_config.NumberColumn(t("pos.current_price"), format="%.2f"),
            "Value": st.column_config.NumberColumn(t("pos.value"), format="%.0f €"),
            "PnL": st.column_config.NumberColumn(t("pos.pnl"), format="%.0f €"),
            "PnLPct": st.column_config.NumberColumn(t("pos.pnl") + " %", format="percent"),
            "Ann": st.column_config.NumberColumn(t("pos.ann"), format="percent"),
            "Weight": st.column_config.NumberColumn(t("chk.col_weight"), format="percent"),
            "Return": st.column_config.NumberColumn(
                t("chk.col_return", period=period), format="percent"
            ),
            "Trend": st.column_config.AreaChartColumn(
                t("chk.col_trend", period=period), width="small"
            ),
        },
        hide_index=True,
        width="stretch",
    )
    if pnl_totals and not pnl_totals.get("cost_known", True):
        st.caption(t("pos.cost_unknown"))

    sec(t("chk.top_problems"))
    problems_list = top_problems(ctx)
    if problems_list:
        for problem in problems_list:
            st.markdown(problem)
    else:
        st.success(t("chk.no_problems"))

    sec(t("chk.risk_eur"))
    _db_for_search = load_market_db()
    st.markdown(
        kpi_row_html(
            [
                {
                    "label": t("chk.kpi_swing"),
                    "value": f"± {eur(total * c['annual_vol'])}",
                    "sub": t("chk.kpi_swing_sub", vol=f"{c['annual_vol']:.1%}")
                    + interpret_volatility(
                        c["annual_vol"],
                        (
                            compute_daily_returns(_db_for_search).std() * TRADING_DAYS**0.5
                            if _db_for_search is not None
                            else None
                        ),
                    ),
                },
                {
                    "label": t("chk.kpi_var"),
                    "value": eur(total * c["var_95"]),
                    "sub": t("chk.kpi_var_sub"),
                },
                {
                    "label": t("chk.kpi_dd"),
                    "value": eur(total * c["drawdown"]),
                    "sub": t("chk.kpi_dd_sub", dd=f"{c['drawdown']:.1%}"),
                },
            ]
        ),
        unsafe_allow_html=True,
    )
    st.caption(t("chk.estimates_caption"))

    sec(t("chk.scenarios"))

    simulations, discarded, has_candidates = scenario_results(ctx)

    for simulation in simulations:
        st.markdown(simulation)
    if not simulations and has_candidates:
        st.markdown(t("chk.no_improve"))
        for text in discarded:
            st.caption(t("chk.discarded") + text)
    for opportunity in find_opportunities(portfolio, c["fund"])[:2]:
        st.markdown(opportunity)
    if not has_candidates:
        st.caption(t("chk.no_scenario"))

    st.divider()
    if ctx.stateful:
        col_pdf, col_log, col_hist = st.columns([1.2, 1, 1.8], gap="large")
    else:
        # Investor è stateless: solo il download PDF, niente "salva analisi"
        # né storico (log_analysis/load_analyses toccano il DB per advisor).
        (col_pdf,) = st.columns([1])
    with col_pdf:
        st.download_button(
            t("chk.pdf_btn"),
            # dati pronti ora, impaginazione del PDF solo al clic (thread separato)
            data=_deferred_report(report_input(ctx, exec_text, problems_list, simulations)),
            file_name=f"portfolio_report_{pd.Timestamp.now():%Y%m%d}.pdf",
            mime="application/pdf",
            width="stretch",
            type="primary",
        )
    if ctx.stateful:
        with col_log:
            save_snapshot_button(ctx)
        with col_hist:
            history_panel(ctx)


# ------------------------------------------------------------------ pezzi riusabili
# Usati sia dal Check-up (Investor) sia dalla Panoramica cliente dell'Advisor:
# stesse regole, stesso PDF, un solo posto da mantenere.


def executive_text(ctx: ViewContext) -> str:
    """Sintesi deterministica delle metriche (nessun testo generato da modelli)."""
    assert ctx.computed is not None
    c = ctx.computed
    return executive_summary(
        ctx.period,
        c["cum_return"],
        c["breakdown"],
        c["contributions"],
        c["avg_corr"],
        c["usd_weight"],
        c["drawdown"],
        c["beta"],
        BENCHMARK,
    )


def top_problems(ctx: ViewContext) -> list[str]:
    """I cinque rilievi principali: alert della seduta, profilo, poi problemi strutturali."""
    assert ctx.computed is not None
    c = ctx.computed
    portfolio, risk_profile = ctx.portfolio, ctx.risk_profile
    problems = find_problems(portfolio, c["fund"], c["contributions"], c["avg_corr"], c["radar"])
    session_markers = (t_in("en", "alert.session_marker"), t_in("it", "alert.session_marker"))
    session_alerts = [
        a
        for a in evaluate_alerts(
            c["returns"], portfolio, c["contributions"], c["avg_corr"], c["drawdown"]
        )
        if any(marker in a for marker in session_markers)
    ]
    if risk_profile in PROFILE_VOL and c["annual_vol"] > PROFILE_VOL[risk_profile]:
        band = PROFILE_VOL[risk_profile]
        problems.insert(
            0,
            t(
                "chk.profile_problem",
                profile=t(f"prof.{risk_profile}").lower(),
                band=f"{band:.0%}",
                excess=f"{c['annual_vol'] / band - 1:.0%}",
            ),
        )
    return (session_alerts + problems)[:5]


def scenario_results(ctx: ViewContext) -> tuple[list[str], list[str], bool]:
    """Scenari di ribilanciamento: (migliorativi, scartati, c'era almeno un candidato)."""
    assert ctx.computed is not None
    c = ctx.computed
    total, portfolio = ctx.total, ctx.portfolio

    def simulate_change(new_pf: list) -> tuple[float, int]:
        new_vol = portfolio_volatility(c["returns"], new_pf) * TRADING_DAYS**0.5
        new_daily = portfolio_daily_returns(c["returns"], new_pf)
        new_dd = max_drawdown((1 + new_daily).cumprod())
        new_radar = radar_scores(new_vol, new_pf, new_dd, c["avg_corr"])
        new_dna = dna_scores(c["fund"], new_pf, new_vol, c["avg_corr"])
        new_breakdown = health_breakdown(new_dna, new_radar, usd_exposure(new_pf))
        return new_vol, portfolio_health_score(new_breakdown)

    weights_sorted = sorted(portfolio, key=lambda p: -p["weight"])
    candidates_sim = {}
    if len(portfolio) >= 2 and weights_sorted[0]["weight"] > 0.25:
        top_t = weights_sorted[0]["ticker"]
        candidates_sim[t("chk.halve", ticker=top_t)] = reduce_position(portfolio, top_t, 0.5)
    if len(portfolio) >= 3 and c["radar"].get("Concentration", 0) > 25:
        candidates_sim[t("chk.equalize")] = equal_weight_portfolio(portfolio)

    simulations: list[str] = []
    discarded: list[str] = []
    for name, new_pf in candidates_sim.items():
        new_vol, new_health = simulate_change(new_pf)
        improves = new_health > c["health"] or (
            new_health == c["health"] and new_vol < c["annual_vol"] * 0.98
        )
        text = t(
            "chk.sim_text",
            name=name,
            vol_from=eur(total * c["annual_vol"]),
            vol_to=eur(total * new_vol),
            h_from=c["health"],
            h_to=new_health,
        )
        (simulations if improves else discarded).append(text)
    return simulations, discarded, bool(candidates_sim)


def report_input(
    ctx: ViewContext,
    exec_text: str,
    problems: list[str],
    simulations: list[str],
    monitoring: list[dict] | None = None,
) -> ReportInput:
    """I dati dei report PDF: un solo calcolo per la versione Investor e quella Advisor."""
    assert ctx.computed is not None
    c = ctx.computed
    amounts, portfolio = ctx.amounts, ctx.portfolio
    lang = st.session_state.get("language", "en")
    weights = pd.Series({p["ticker"]: float(p["weight"]) for p in portfolio}, dtype=float)
    metrics = compute_report_metrics(
        c["pf_daily"],
        c["bench_daily"],
        weights,
        c["contributions"],
        c["fund"],
        c["usd_weight"],
        risk_free=ctx.risk_free,
        unclassified=t_in(lang, "pdf.not_classified"),
    )
    # copertura dati: titoli con storico più corto della finestra selezionata
    window_start = c["prices"].index[0]
    coverage = []
    for ticker in sorted(amounts):
        first_price = c["prices"][ticker].first_valid_index()
        if first_price is not None and (first_price - window_start).days > 7:
            coverage.append(
                t_in(lang, "cov.note", ticker=ticker, date=f"{pd.Timestamp(first_price):%d/%m/%Y}")
            )
    sectors = c["fund"]["sector"] if "sector" in c["fund"].columns else pd.Series(dtype=object)
    pnl_totals = ctx.pnl_totals or {}
    source = yahoo_client.last_price_source
    return ReportInput(
        portfolio_name=ctx.portfolio_name,
        positions=amounts,
        period=ctx.period,
        metrics=metrics,
        pf_value=c["pf_value"],
        bench_value=(1 + c["bench_daily"]).cumprod(),
        health=c["health"],
        breakdown=c["breakdown"],
        executive=exec_text,
        lang=lang,
        benchmark=BENCHMARK,
        in_eur=ctx.in_eur,
        names=ctx.names,
        sector_of={k: str(v) for k, v in sectors.dropna().items() if str(v)},
        monthly=monthly_returns(c["pf_daily"], 12),
        bench_monthly=monthly_returns(c["bench_daily"], 12),
        per_ticker_returns=per_ticker_cumulative_return(c["prices"]),
        per_ticker_pnl=ctx.pos["pnl"] if ctx.pos is not None else None,
        observations=problems + find_opportunities(portfolio, c["fund"])[:2],
        what_if=simulations,
        stress=stress_tests(c["returns"], weights, metrics, include_fx=ctx.in_eur),
        # proiezione Monte Carlo solo nei PDF dell'area Advisor: Investor non fa previsioni
        projection=report_projection(ctx) if ctx.stateful else None,
        monitoring=monitoring,
        risk_profile=ctx.risk_profile,
        profile_band=PROFILE_VOL.get(ctx.risk_profile),
        advisor=ctx.advisor if ctx.advisor != DEV_ADVISOR else None,
        recipient=ctx.report_recipient or None,
        risk_free=ctx.risk_free,
        invested=pnl_totals.get("cost"),
        pnl=pnl_totals.get("pnl"),
        pnl_pct=pnl_totals.get("pnl_pct"),
        coverage_notes=coverage,
        price_source="" if source in ("", "—") else source,
        advisor_issued=ctx.stateful,
    )


def _deferred_report(report: ReportInput):
    return lambda: build_investor_report(report)


def report_pdf(
    ctx: ViewContext, exec_text: str, problems: list[str], simulations: list[str]
) -> bytes:
    """Il report Investor (quattro pagine) del portafoglio in `ctx`."""
    return build_investor_report(report_input(ctx, exec_text, problems, simulations))


def advisor_report_pdf(
    ctx: ViewContext,
    exec_text: str,
    problems: list[str],
    simulations: list[str],
    monitoring: list[dict] | None = None,
) -> bytes:
    """Il report Advisor (revisione del portafoglio) del cliente in `ctx`."""
    return build_advisor_report(report_input(ctx, exec_text, problems, simulations, monitoring))


def save_snapshot_button(ctx: ViewContext) -> None:
    """Registra l'analisi nello storico del consulente (solo Advisor)."""
    assert ctx.computed is not None
    c = ctx.computed
    if st.button(t("chk.save_btn"), width="stretch"):
        log_analysis(
            ctx.advisor,
            ctx.portfolio_name,
            ctx.period,
            ctx.total,
            c["cum_return"],
            c["risk_score"],
            health=c["health"],
        )
        log_audit(ctx.advisor, "run_analysis", ctx.portfolio_name)
        st.toast(t("chk.saved_toast"))


def history_panel(ctx: ViewContext) -> None:
    """Storico delle analisi salvate del consulente, con l'andamento dell'Health Score."""
    history = load_analyses(ctx.advisor)
    portfolio_name = ctx.portfolio_name
    if not history.empty:
        with st.expander(t("chk.history", n=len(history))):
            trend = history.dropna(subset=["health"])
            trend = trend[trend["portfolio"] == portfolio_name]
            if len(trend) >= 2:
                series = pd.Series(
                    trend["health"].to_numpy(dtype=float),
                    index=pd.to_datetime(trend["timestamp"]),
                ).sort_index()
                st.altair_chart(simple_line(series, y_format=".0f"), width="stretch")
                delta_h = int(series.iloc[-1] - series.iloc[0])
                st.caption(t("chk.history_caption", name=portfolio_name, delta=f"{delta_h:+d}"))
            st.dataframe(
                history,
                column_config={
                    "timestamp": st.column_config.TextColumn(t("chk.hist_date")),
                    "portfolio": st.column_config.TextColumn(t("chk.hist_portfolio")),
                    "period": st.column_config.TextColumn(t("chk.hist_period")),
                    "invested": st.column_config.NumberColumn(
                        t("chk.hist_invested"), format="%.0f €"
                    ),
                    "cum_return": st.column_config.NumberColumn(
                        t("chk.hist_return"), format="percent"
                    ),
                    "risk_score": st.column_config.NumberColumn(t("chk.hist_risk")),
                    "health": st.column_config.NumberColumn(t("chk.hist_health")),
                },
                hide_index=True,
            )
