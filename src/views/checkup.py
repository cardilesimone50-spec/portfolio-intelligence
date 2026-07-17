"""Vista Check-up: hero, executive summary, problemi, rischio in euro, PDF."""

import pandas as pd
import streamlit as st

from src.analytics.alerts import evaluate_alerts
from src.analytics.insights import (
    dna_label,
    dna_scores,
    equal_weight_portfolio,
    executive_summary,
    find_opportunities,
    find_problems,
    generate_insights,
    generate_suggestions,
    health_breakdown,
    monthly_returns,
    portfolio_health_score,
    radar_scores,
    reduce_position,
    usd_exposure,
)
from src.analytics.interpret import (
    interpret_beta,
    interpret_correlation,
    interpret_drawdown,
    interpret_sharpe,
    interpret_sortino,
    interpret_volatility,
)
from src.analytics.performance import (
    annualized_geometric_return,
    annualized_sharpe,
    expected_shortfall,
    max_drawdown,
    sharpe_from_daily,
    sortino_from_daily,
    sortino_ratio,
    value_at_risk,
)
from src.analytics.simulation import simulate_shock
from src.data.store import load_analyses, log_analysis
from src.i18n import t, t_in
from src.portfolio.returns import (
    compute_daily_returns,
    per_ticker_cumulative_return,
    portfolio_daily_returns,
)
from src.portfolio.risk import portfolio_volatility
from src.ui.components import breakdown_html, eur, hero_html, kpi_row_html, sec
from src.ui.identity import DEV_ADVISOR
from src.views.common import BENCHMARK, PROFILE_VOL, TRADING_DAYS, load_market_db
from src.views.context import ViewContext
from src.visualization.charts import LOSS, equity_area, simple_line
from src.visualization.pdf_report import build_report


def render(ctx: ViewContext) -> None:
    c = ctx.computed
    amounts, total, portfolio = ctx.amounts, ctx.total, ctx.portfolio
    period, risk_free, risk_profile = ctx.period, ctx.risk_free, ctx.risk_profile
    advisor, portfolio_name, in_eur = ctx.advisor, ctx.portfolio_name, ctx.in_eur

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
        exec_text = executive_summary(
            period,
            c["cum_return"],
            c["breakdown"],
            c["contributions"],
            c["avg_corr"],
            c["usd_weight"],
            c["drawdown"],
            c["beta"],
            BENCHMARK,
        )
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
            "Current": float(pos["current_price"].get(ticker)) if len(pos) else None,
            "Value": amounts[ticker],
            "PnL": float(pos["pnl"].get(ticker)) if len(pos) else None,
            "PnLPct": float(pos["pnl_pct"].get(ticker)) if len(pos) else None,
            "Weight": amounts[ticker] / total,
            "Return": cum_by_ticker.get(ticker),
            "Trend": normalized_pos[ticker].dropna().tolist()[-130:],
        }
        for ticker in sorted(amounts, key=amounts.get, reverse=True)
    ]
    st.dataframe(
        pd.DataFrame(position_rows),
        column_config={
            "Ticker": st.column_config.TextColumn(t("chk.col_ticker")),
            "Company": st.column_config.TextColumn(t("chk.col_company")),
            "Qty": st.column_config.NumberColumn(t("pos.qty"), format="%.4g"),
            "Buy": st.column_config.NumberColumn(t("pos.buy_price"), format="%.2f"),
            "Current": st.column_config.NumberColumn(t("pos.current_price"), format="%.2f"),
            "Value": st.column_config.NumberColumn(t("pos.value"), format="%.0f €"),
            "PnL": st.column_config.NumberColumn(t("pos.pnl"), format="%.0f €"),
            "PnLPct": st.column_config.NumberColumn(t("pos.pnl") + " %", format="percent"),
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
    top_problems = (session_alerts + problems)[:5]
    if top_problems:
        for problem in top_problems:
            st.markdown(problem)
    else:
        st.success(t("chk.no_problems"))

    sec(t("chk.risk_eur"))
    _db_for_search = load_market_db()
    st.markdown(
        kpi_row_html(
            [
                {
                    "icon": "wave",
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
                    "icon": "bolt",
                    "label": t("chk.kpi_var"),
                    "value": eur(total * c["var_95"]),
                    "sub": t("chk.kpi_var_sub"),
                    "color": LOSS,
                },
                {
                    "icon": "down",
                    "label": t("chk.kpi_dd"),
                    "value": eur(total * c["drawdown"]),
                    "sub": t("chk.kpi_dd_sub", dd=f"{c['drawdown']:.1%}"),
                    "color": LOSS,
                },
            ]
        ),
        unsafe_allow_html=True,
    )
    st.caption(t("chk.estimates_caption"))

    sec(t("chk.scenarios"))

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

    simulations, discarded = [], []
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

    for simulation in simulations:
        st.markdown(simulation)
    if not simulations and candidates_sim:
        st.markdown(t("chk.no_improve"))
        for text in discarded:
            st.caption(t("chk.discarded") + text)
    for opportunity in find_opportunities(portfolio, c["fund"])[:2]:
        st.markdown(opportunity)
    if not candidates_sim:
        st.caption(t("chk.no_scenario"))

    st.divider()
    col_pdf, col_log, col_hist = st.columns([1.2, 1, 1.8], gap="large")
    with col_pdf:
        insights = generate_insights(
            period,
            c["cum_return"],
            c["contributions"],
            c["avg_corr"],
            c["drawdown"],
            c["beta"],
            BENCHMARK,
        )
        report_sharpe = annualized_sharpe(c["returns"], portfolio, risk_free_rate=risk_free)
        report_sortino = sortino_ratio(c["returns"], portfolio, risk_free_rate=risk_free)
        universe_vols_report = (
            compute_daily_returns(_db_for_search).std() * TRADING_DAYS**0.5
            if _db_for_search is not None
            else None
        )
        # controparte benchmark per ogni metrica confrontabile ("ho battuto il mercato?")
        bench_value_report = (1 + c["bench_daily"]).cumprod()
        bench_cum = float(bench_value_report.iloc[-1] - 1)
        bench_cagr = annualized_geometric_return(c["bench_daily"])
        bench_vol = float(c["bench_daily"].std()) * TRADING_DAYS**0.5
        bench_sharpe = sharpe_from_daily(c["bench_daily"], risk_free_rate=risk_free)
        bench_sortino = sortino_from_daily(c["bench_daily"], risk_free_rate=risk_free)
        bench_dd = max_drawdown(bench_value_report)
        bench_var = value_at_risk(c["bench_daily"])
        pf_es = expected_shortfall(c["pf_daily"])
        bench_es = expected_shortfall(c["bench_daily"])
        metric_rows = [
            (
                t("m.return", period=period),
                f"{c['cum_return']:+.1%}",
                f"{bench_cum:+.1%}",
                t("r.return"),
            ),
            (
                t("m.cagr"),
                f"{c['annual_ret']:+.1%}",
                f"{bench_cagr:+.1%}",
                t("r.cagr"),
            ),
            (
                t("m.vol"),
                f"{c['annual_vol']:.1%}",
                f"{bench_vol:.1%}",
                interpret_volatility(c["annual_vol"], universe_vols_report),
            ),
            (
                t("m.sharpe"),
                f"{report_sharpe:.2f}",
                f"{bench_sharpe:.2f}",
                interpret_sharpe(report_sharpe),
            ),
            (
                t("m.sortino"),
                f"{report_sortino:.2f}",
                f"{bench_sortino:.2f}",
                interpret_sortino(report_sortino, report_sharpe),
            ),
            (
                t("m.maxdd"),
                f"{c['drawdown']:.1%}",
                f"{bench_dd:.1%}",
                interpret_drawdown(c["drawdown"]),
            ),
            (
                t("m.var"),
                f"{c['var_95']:.1%}",
                f"{bench_var:.1%}",
                t("r.var", amount=eur(total * c["var_95"])),
            ),
            (
                t("m.es"),
                f"{pf_es:.1%}",
                f"{bench_es:.1%}",
                t("r.es", amount=eur(total * pf_es)),
            ),
            (
                t("m.beta", benchmark=BENCHMARK),
                f"{c['beta']:.2f}",
                "—",
                interpret_beta(c["beta"], BENCHMARK),
            ),
            (
                t("m.alpha", benchmark=BENCHMARK),
                f"{c['alpha']:+.1%}/yr",
                "—",
                t("r.alpha"),
            ),
            (
                t("m.corr"),
                f"{c['avg_corr']:.2f}",
                "—",
                interpret_correlation(c["avg_corr"]),
            ),
        ]
        # adeguatezza: volatilità osservata contro la soglia del profilo dichiarato
        report_suitability = None
        if risk_profile in PROFILE_VOL:
            profile_band = PROFILE_VOL[risk_profile]
            report_suitability = {
                "ok": c["annual_vol"] <= profile_band,
                "text": t(
                    "suit.text",
                    vol=f"{c['annual_vol']:.1%}",
                    band=f"{profile_band:.0%}",
                    profile=t(f"prof.{risk_profile}").lower(),
                ),
            }
        # allocazione settoriale pesata per capitale (dai profili Yahoo Finance)
        report_sectors = None
        if "sector" in c["fund"].columns:
            sector_by_ticker = (
                c["fund"]["sector"].reindex(list(amounts)).fillna(t("pdf.not_classified"))
            )
            report_sectors = (
                (pd.Series(amounts, dtype=float) / total).groupby(sector_by_ticker).sum()
            )
        # copertura dati: titoli con storico più corto della finestra selezionata
        window_start = c["prices"].index[0]
        report_coverage = []
        for ticker_cov in sorted(amounts):
            first_price = c["prices"][ticker_cov].first_valid_index()
            if first_price is not None and (first_price - window_start).days > 7:
                report_coverage.append(
                    t(
                        "cov.note",
                        ticker=ticker_cov,
                        date=f"{pd.Timestamp(first_price):%d/%m/%Y}",
                    )
                )
        top_ticker_report = max(amounts, key=amounts.get)
        try:
            shock_report = simulate_shock(c["returns"], portfolio, top_ticker_report, -0.20)
            report_scenario = {
                "label": t(
                    "scen.label",
                    ticker=top_ticker_report,
                    weight=f"{amounts[top_ticker_report] / total:.0%}",
                ),
                "direct": shock_report["direct"],
                "total": shock_report["total"],
            }
        except ValueError:
            report_scenario = None
        st.download_button(
            t("chk.pdf_btn"),
            data=build_report(
                portfolio_name=portfolio_name,
                positions=amounts,
                period=period,
                cum_return=c["cum_return"],
                health_score=c["health"],
                metric_rows=metric_rows,
                insights=insights + top_problems,
                suggestions=simulations
                + generate_suggestions(c["dna"], c["radar"], c["contributions"])
                + find_opportunities(portfolio, c["fund"]),
                names=ctx.names,
                advisor=advisor if advisor != DEV_ADVISOR else None,
                risk_profile=risk_profile,
                benchmark=BENCHMARK,
                currency_note=t("pdf.currency_eur") if in_eur else t("pdf.currency_orig"),
                executive=exec_text,
                suitability=report_suitability,
                annual_return=c["annual_ret"],
                pf_value=c["pf_value"],
                bench_value=bench_value_report,
                monthly=monthly_returns(c["pf_daily"], 12),
                contributions=c["contributions"],
                breakdown=c["breakdown"],
                per_ticker_returns=cum_by_ticker,
                sector_weights=report_sectors,
                scenario=report_scenario,
                coverage_notes=report_coverage,
                risk_free=risk_free,
                invested=pnl_totals.get("cost"),
                pnl=pnl_totals.get("pnl"),
                pnl_pct=pnl_totals.get("pnl_pct"),
                per_ticker_pnl=ctx.pos["pnl"] if ctx.pos is not None else None,
                lang=st.session_state.get("language", "en"),
            ),
            file_name=f"portfolio_report_{pd.Timestamp.now():%Y%m%d}.pdf",
            mime="application/pdf",
            width="stretch",
            type="primary",
        )
    with col_log:
        if st.button(t("chk.save_btn"), width="stretch"):
            log_analysis(
                advisor,
                portfolio_name,
                period,
                total,
                c["cum_return"],
                c["risk_score"],
                health=c["health"],
            )
            st.toast(t("chk.saved_toast"))
    with col_hist:
        history = load_analyses(advisor)
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
                    st.caption(
                        t("chk.history_caption", name=portfolio_name, delta=f"{delta_h:+d}")
                    )
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
                        "risk_score": st.column_config.NumberColumn("Risk /100"),
                        "health": st.column_config.NumberColumn("Health /100"),
                    },
                    hide_index=True,
                )
