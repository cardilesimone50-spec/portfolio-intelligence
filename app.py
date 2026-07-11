"""Portfolio Intelligence — dashboard Streamlit.

Avvio: streamlit run app.py
"""

import pandas as pd
import streamlit as st

from src.analytics.alerts import evaluate_alerts
from src.analytics.backtest import (
    buy_and_hold,
    equal_weight,
    max_sharpe,
    min_variance,
    momentum_top,
    run_backtest,
)
from src.analytics.insights import (
    dna_label,
    dna_scores,
    generate_insights,
    generate_suggestions,
    monthly_returns,
    portfolio_risk_score,
    radar_scores,
    risk_contributions,
    stock_scores,
)
from src.analytics.performance import (
    annualized_sharpe,
    beta_alpha,
    max_drawdown,
    sortino_ratio,
    value_at_risk,
)
from src.analytics.simulation import simulate_shock
from src.data.cache import load_nasdaq100_prices
from src.data.importers import parse_positions
from src.data.store import (
    list_portfolios,
    load_analyses,
    log_analysis,
    save_portfolio,
)
from src.data.store import load_prices as load_stored_prices
from src.data.yahoo_client import fetch_price_history
from src.fundamentals.valuation import fetch_fundamentals
from src.visualization.pdf_report import build_report
from src.portfolio.optimization import (
    efficient_frontier,
    max_sharpe_weights,
    minimum_variance_weights,
)
from src.portfolio.returns import (
    compute_daily_returns,
    per_ticker_cumulative_return,
    portfolio_daily_returns,
    portfolio_expected_return,
)
from src.portfolio.risk import (
    average_pairwise_correlation,
    correlation_matrix,
    correlations_with,
    portfolio_volatility,
)
from src.visualization.charts import (
    PALETTE,
    allocation_bars,
    correlation_bars,
    correlation_heatmap,
    efficient_frontier_chart,
    galaxy_chart,
    monthly_bars,
    radar_chart,
)

BENCHMARK = "QQQ"  # ETF sul Nasdaq-100
TRADING_DAYS = 252
PERIOD_DAYS = {"1 mese": 30, "6 mesi": 182, "1 anno": 365, "2 anni": 730, "5 anni": 1826}

st.set_page_config(page_title="Portfolio Intelligence", page_icon="📈", layout="wide")

st.markdown(
    """
    <style>
    .block-container { padding-top: 2rem; }
    [data-testid="stMetric"] {
        background: linear-gradient(145deg, rgba(57,135,229,0.10), rgba(57,135,229,0.03));
        border: 1px solid rgba(140, 160, 190, 0.15);
        border-radius: 16px;
        padding: 16px 18px;
    }
    [data-testid="stMetricLabel"] { opacity: 0.7; }
    .hero {
        background: linear-gradient(160deg, #161a22 0%, #10141c 60%, #131926 100%);
        border: 1px solid rgba(140, 160, 190, 0.18);
        border-radius: 20px;
        padding: 28px 32px;
        text-align: center;
    }
    .hero-label { font-size: 0.8rem; letter-spacing: 0.18em; opacity: 0.6; }
    .hero-value { font-size: 2.6rem; font-weight: 700; margin: 6px 0 2px; }
    .hero-return { font-size: 1.1rem; font-weight: 600; }
    .hero-return.pos { color: #e66767; }
    .hero-return.neg { color: #3987e5; }
    .risk-label { font-size: 0.8rem; opacity: 0.6; margin-top: 18px; text-align: left; }
    .risk-track {
        background: rgba(140,160,190,0.15); border-radius: 6px; height: 10px;
        margin-top: 6px; overflow: hidden;
    }
    .risk-fill {
        height: 100%; border-radius: 6px;
        background: linear-gradient(90deg, #199e70, #c98500, #e66767);
    }
    .dna-card, .ai-card {
        background: #161a22;
        border: 1px solid rgba(140, 160, 190, 0.15);
        border-radius: 20px;
        padding: 22px 26px;
        height: 100%;
    }
    .dna-title { font-size: 0.8rem; letter-spacing: 0.18em; opacity: 0.6; margin-bottom: 14px; }
    .dna-row { display: flex; align-items: center; margin: 9px 0; gap: 10px; }
    .dna-name { width: 70px; font-size: 0.9rem; opacity: 0.85; }
    .dna-track { flex: 1; background: rgba(140,160,190,0.15); border-radius: 5px; height: 8px; }
    .dna-fill { height: 100%; border-radius: 5px; background: #3987e5; }
    .dna-fill.risk { background: #c98500; }
    .dna-value { width: 40px; text-align: right; font-size: 0.9rem; }
    .dna-status { margin-top: 16px; font-weight: 600; font-size: 1.05rem; }
    .ai-card p { margin: 0 0 10px; line-height: 1.5; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=3600, show_spinner="Scarico i prezzi da Yahoo Finance...")
def cached_prices(tickers: tuple[str, ...], period: str) -> pd.DataFrame:
    return fetch_price_history(list(tickers), period=period)


@st.cache_data(ttl=3600, show_spinner="Scarico i fondamentali da Yahoo Finance...")
def cached_fundamentals(tickers: tuple[str, ...]) -> pd.DataFrame:
    return fetch_fundamentals(list(tickers))


def eur(value: float) -> str:
    return f"{value:,.0f} €".replace(",", ".")


def load_market_db() -> pd.DataFrame | None:
    prices = load_stored_prices()
    if prices is not None:
        return prices
    return load_nasdaq100_prices()


def dna_card_html(dna: dict[str, float], label: str) -> str:
    rows = ""
    for name, score in dna.items():
        css = "risk" if name == "Risk" else ""
        rows += (
            f'<div class="dna-row"><div class="dna-name">{name}</div>'
            f'<div class="dna-track"><div class="dna-fill {css}" '
            f'style="width:{score:.0f}%"></div></div>'
            f'<div class="dna-value">{score:.0f}</div></div>'
        )
    return (
        f'<div class="dna-card"><div class="dna-title">PORTFOLIO DNA</div>{rows}'
        f'<div class="dna-status">{label}</div></div>'
    )


st.title("Portfolio Intelligence")

tab_dash, tab_analysis, tab_corr, tab_fundamentals, tab_nasdaq, tab_backtest = st.tabs(
    ["🏠  Dashboard", "📊  Analisi", "🔗  Chi si muove insieme",
     "🏢  Fondamentali", "🏆  Nasdaq-100", "⏮  Backtest"]
)

computed: dict | None = None

# ---------------------------------------------------------------- dashboard
with tab_dash:
    col_editor, col_hero, col_dna = st.columns([1, 1.1, 1.1], gap="large")

    with col_editor:
        st.markdown("**Composizione** — modifica liberamente")
        positions = st.data_editor(
            pd.DataFrame({"ticker": ["AAPL", "MSFT", "NVDA"], "importo": [4000, 3000, 3000]}),
            num_rows="dynamic",
            hide_index=True,
            column_config={
                "ticker": st.column_config.TextColumn("Titolo", required=True),
                "importo": st.column_config.NumberColumn(
                    "Importo", min_value=0.0, step=500.0, format="%d €", required=True
                ),
            },
            key="positions",
        )
        period = st.selectbox(
            "Orizzonte storico", ["1mo", "6mo", "1y", "2y", "5y"], index=2, key="pf_period"
        )

        with st.expander("📂 Importa da CSV/Excel"):
            uploaded = st.file_uploader(
                "Estratto del broker (colonne ticker + importo)",
                type=["csv", "xlsx", "xls"],
            )
        saved = list_portfolios()
        with st.expander("💾 Portafogli salvati"):
            selected_saved = st.selectbox(
                "Carica un portafoglio", ["— usa l'editor —"] + sorted(saved), index=0
            )
            portfolio_name = st.text_input("Nome", value="Il mio portafoglio")
            want_save = st.button("Salva la composizione attiva")

    amounts = {
        str(row.ticker).upper().strip(): float(row.importo)
        for row in positions.itertuples()
        if str(row.ticker).strip() and float(row.importo or 0) > 0
    }
    # precedenza: file importato > portafoglio salvato > editor
    source = "editor"
    if uploaded is not None:
        try:
            amounts = parse_positions(uploaded.getvalue(), uploaded.name)
            source = f"file «{uploaded.name}»"
        except ValueError as exc:
            st.error(f"Import fallito: {exc}")
    elif selected_saved != "— usa l'editor —":
        amounts = dict(saved[selected_saved])
        source = f"portafoglio «{selected_saved}»"
        portfolio_name = selected_saved

    if source != "editor":
        with col_editor:
            st.caption(f"⚡ Composizione attiva: {source} — rimuovi file/selezione "
                       "per tornare all'editor.")
    if want_save and amounts:
        save_portfolio(portfolio_name, amounts)
        st.toast(f"Portafoglio «{portfolio_name}» salvato ✓")

    total = sum(amounts.values())
    portfolio = (
        [{"ticker": t, "weight": amount / total} for t, amount in amounts.items()] if total else []
    )

    if not portfolio:
        st.info("Aggiungi almeno un titolo con un importo positivo.")
    else:
        try:
            tickers = tuple(sorted(amounts))
            prices = cached_prices(tickers, period)
            returns = compute_daily_returns(prices)

            pf_daily = portfolio_daily_returns(returns, portfolio)
            pf_value = (1 + pf_daily).cumprod()
            cum_return = float(pf_value.iloc[-1] - 1)

            annual_ret = portfolio_expected_return(returns, portfolio) * TRADING_DAYS
            annual_vol = portfolio_volatility(returns, portfolio) * TRADING_DAYS**0.5
            drawdown = max_drawdown(pf_value)
            min_periods = max(15, min(60, len(returns) // 2))
            avg_corr = average_pairwise_correlation(returns, min_periods=min_periods)

            bench_prices = cached_prices((BENCHMARK,), period)
            bench_daily = compute_daily_returns(bench_prices)[BENCHMARK]
            beta, alpha = beta_alpha(pf_daily, bench_daily)

            contributions = risk_contributions(returns, portfolio)
            radar = radar_scores(annual_vol, portfolio, drawdown, avg_corr)
            risk_score = portfolio_risk_score(radar)

            fund = cached_fundamentals(tickers)
            dna = dna_scores(fund, portfolio, annual_vol, avg_corr)

            computed = {
                "returns": returns, "prices": prices, "pf_daily": pf_daily,
                "annual_ret": annual_ret, "annual_vol": annual_vol,
                "drawdown": drawdown, "avg_corr": avg_corr,
                "beta": beta, "alpha": alpha, "min_periods": min_periods,
            }

            with col_hero:
                css = "pos" if cum_return >= 0 else "neg"
                st.markdown(
                    f"""<div class="hero">
                    <div class="hero-label">IL TUO PORTAFOGLIO</div>
                    <div class="hero-value">{eur(total * (1 + cum_return))}</div>
                    <div class="hero-return {css}">{cum_return:+.1%} nel periodo ({period})</div>
                    <div class="risk-label">RISCHIO &nbsp;{risk_score}/100</div>
                    <div class="risk-track"><div class="risk-fill"
                         style="width:{risk_score}%"></div></div>
                    </div>""",
                    unsafe_allow_html=True,
                )
                st.caption(
                    f"Valore = {eur(total)} investiti oggi, rivalutati con "
                    "l'andamento storico del periodo."
                )

            with col_dna:
                if dna:
                    st.markdown(dna_card_html(dna, dna_label(dna)), unsafe_allow_html=True)

            for alert in evaluate_alerts(returns, portfolio, contributions, avg_corr, drawdown):
                st.warning(alert)

            col_ai, col_radar = st.columns([1.3, 1], gap="large")
            with col_ai:
                st.markdown("#### 🤖 Analisi automatica")
                insights = generate_insights(
                    period, cum_return, contributions, avg_corr, drawdown, beta, BENCHMARK
                )
                st.markdown(
                    '<div class="ai-card">'
                    + "".join(f"<p>{i}</p>" for i in insights)
                    + "</div>",
                    unsafe_allow_html=True,
                )
                st.caption(
                    "Generata con regole deterministiche sui tuoi dati, non da un modello."
                )
            with col_radar:
                st.markdown("#### 🎯 Radar di rischio")
                st.altair_chart(radar_chart(radar), use_container_width=True)

            col_galaxy, col_timeline = st.columns([1.15, 1], gap="large")
            with col_galaxy:
                st.markdown("#### 🪐 La tua galassia")
                st.caption(
                    "Dimensione = peso · colore = rendimento · vicinanza = correlazione"
                )
                if len(tickers) >= 2:
                    corr = correlation_matrix(returns, min_periods=min_periods)
                    weights_s = pd.Series({p["ticker"]: p["weight"] for p in portfolio})
                    cum_by_ticker = per_ticker_cumulative_return(prices)
                    st.altair_chart(
                        galaxy_chart(corr, weights_s, cum_by_ticker),
                        use_container_width=True,
                    )
                else:
                    st.info("Servono almeno 2 titoli.")
            with col_timeline:
                st.markdown("#### 📅 Mese per mese")
                monthly = monthly_returns(pf_daily)
                if len(monthly) >= 2:
                    st.altair_chart(monthly_bars(monthly), use_container_width=True)
                    best, worst = monthly.idxmax(), monthly.idxmin()
                    st.caption(
                        f"Mese migliore: **{best.strftime('%b %Y')}** "
                        f"({monthly.max():+.1%}) · peggiore: "
                        f"**{worst.strftime('%b %Y')}** ({monthly.min():+.1%})"
                    )
                else:
                    st.info("Periodo troppo corto per la vista mensile.")

            st.divider()
            st.markdown("#### 🧪 Simulatore \"What if?\"")
            col_sim_in, col_sim_out = st.columns([1, 2], gap="large")
            with col_sim_in:
                sim_ticker = st.selectbox("Se questo titolo...", sorted(amounts))
                shock_pct = st.slider(
                    "...si muovesse di", -50, 50, -20, step=5, format="%d%%"
                )
            with col_sim_out:
                impact = simulate_shock(returns, portfolio, sim_ticker, shock_pct / 100)
                new_value = total * (1 + impact["total"])
                s1, s2, s3 = st.columns(3)
                s1.metric("Portafoglio oggi", eur(total))
                s2.metric(
                    "Dopo lo shock (con contagio)",
                    eur(new_value),
                    delta=f"{impact['total']:+.1%}",
                )
                s3.metric(
                    "Solo effetto diretto",
                    eur(total * (1 + impact["direct"])),
                    delta=f"{impact['direct']:+.1%}",
                    delta_color="off",
                )
                st.caption(
                    "Il contagio stima come gli altri titoli reagirebbero, "
                    "usando i loro beta storici verso il titolo colpito."
                )

            st.divider()
            col_pdf, col_log, col_hist = st.columns([1, 1, 2], gap="large")
            with col_pdf:
                report_metrics = {
                    "Sharpe ratio": f"{annualized_sharpe(returns, portfolio):.2f}",
                    "Sortino ratio": f"{sortino_ratio(returns, portfolio):.2f}",
                    "Perdita massima storica": f"{drawdown:.1%}",
                    "VaR 95% (1 giorno)": eur(total * value_at_risk(pf_daily)),
                    f"Beta vs {BENCHMARK}": f"{beta:.2f}",
                    "Correlazione media": f"{avg_corr:.2f}",
                }
                st.download_button(
                    "📄 Genera Investment Report (PDF)",
                    data=build_report(
                        portfolio_name=portfolio_name,
                        positions=amounts,
                        period=period,
                        cum_return=cum_return,
                        risk_score=risk_score,
                        metrics=report_metrics,
                        insights=insights,
                        suggestions=generate_suggestions(dna, radar, contributions),
                    ),
                    file_name=f"portfolio_report_{pd.Timestamp.now():%Y%m%d}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
            with col_log:
                if st.button("📝 Salva analisi nello storico", use_container_width=True):
                    log_analysis(portfolio_name, period, total, cum_return, risk_score)
                    st.toast("Analisi salvata ✓")
            with col_hist:
                history = load_analyses()
                if not history.empty:
                    with st.expander(f"🕘 Storico analisi ({len(history)})"):
                        st.dataframe(
                            history,
                            column_config={
                                "timestamp": st.column_config.TextColumn("Data"),
                                "portfolio": st.column_config.TextColumn("Portafoglio"),
                                "period": st.column_config.TextColumn("Periodo"),
                                "invested": st.column_config.NumberColumn(
                                    "Investito", format="%.0f €"
                                ),
                                "cum_return": st.column_config.NumberColumn(
                                    "Rendimento", format="percent"
                                ),
                                "risk_score": st.column_config.NumberColumn("Rischio /100"),
                            },
                            hide_index=True,
                        )
        except ValueError as exc:
            st.error(f"{exc}")

# ---------------------------------------------------------------- analisi
with tab_analysis:
    if computed is None:
        st.info("Configura il portafoglio nella tab Dashboard.")
    else:
        returns = computed["returns"]
        prices = computed["prices"]
        pf_daily = computed["pf_daily"]

        sharpe = annualized_sharpe(returns, portfolio)
        sortino = sortino_ratio(returns, portfolio)
        var_95 = value_at_risk(pf_daily)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Investimento", eur(total))
        m2.metric(
            "Guadagno atteso in 1 anno",
            eur(total * computed["annual_ret"]),
            delta=f"{computed['annual_ret']:+.1%}",
        )
        m3.metric(
            "Oscillazione tipica in 1 anno",
            f"± {eur(total * computed['annual_vol'])}",
            delta=f"{computed['annual_vol']:.1%}",
            delta_color="off",
        )
        m4.metric(
            "Sharpe ratio", f"{sharpe:.2f}",
            help="Rendimento per unità di rischio: sopra 1 è buono, sopra 2 ottimo.",
        )

        r1, r2, r3, r4 = st.columns(4)
        r1.metric(
            "Sortino ratio", f"{sortino:.2f}",
            help="Come lo Sharpe ma conta solo i giorni negativi.",
        )
        r2.metric(
            "Perdita massima storica", f"{computed['drawdown']:.1%}",
            help="Max drawdown: la peggior discesa dal picco nel periodo scelto.",
        )
        r3.metric(
            "VaR 95% (1 giorno)", eur(total * var_95),
            help="Nel 95% dei giorni non perdi più di questa cifra (stima storica).",
        )
        r4.metric(
            f"Beta vs {BENCHMARK}", f"{computed['beta']:.2f}",
            delta=f"α {computed['alpha']:+.1%}/anno", delta_color="off",
            help="Beta 1 = ti muovi come il Nasdaq-100; >1 amplifichi.",
        )
        st.caption("Stime basate sull'andamento storico: non sono una previsione.")

        col_alloc, col_norm = st.columns([1, 1.6], gap="large")
        with col_alloc:
            st.markdown("**Come sono distribuiti i tuoi soldi**")
            st.altair_chart(allocation_bars(amounts), use_container_width=True)
        with col_norm:
            st.markdown("**Se avessi investito 100 € in ciascun titolo**")
            normalized = prices / prices.iloc[0] * 100
            st.line_chart(normalized, color=PALETTE[: len(normalized.columns)], height=300)

        if len(amounts) >= 2:
            st.divider()
            st.markdown("### 💡 Puoi fare di meglio? Ottimizzazione di Markowitz")
            st.caption(
                "La linea grigia è la frontiera efficiente: per ogni livello di rischio, "
                "il miglior rendimento raggiungibile combinando i tuoi titoli."
            )

            candidates = {
                "Attuale": pd.Series({p["ticker"]: p["weight"] for p in portfolio}),
                "Minimo rischio": minimum_variance_weights(returns),
                "Massimo Sharpe": max_sharpe_weights(returns),
            }

            def pf_stats(weights: pd.Series) -> tuple[float, float]:
                pf = [
                    {"ticker": t, "weight": float(w)} for t, w in weights.items() if w > 0
                ]
                ret = portfolio_expected_return(returns, pf) * TRADING_DAYS
                vol = portfolio_volatility(returns, pf) * TRADING_DAYS**0.5
                return ret, vol

            points = pd.DataFrame(
                [
                    {"nome": name, "annual_return": r, "annual_volatility": v}
                    for name, (r, v) in ((n, pf_stats(w)) for n, w in candidates.items())
                ]
            )

            col_frontier, col_compare = st.columns([3, 2], gap="large")
            with col_frontier:
                st.altair_chart(
                    efficient_frontier_chart(efficient_frontier(returns), points),
                    use_container_width=True,
                )
            with col_compare:
                st.markdown("**Confronto**")
                compare = points.set_index("nome")
                compare["sharpe"] = compare["annual_return"] / compare["annual_volatility"]
                st.dataframe(
                    compare,
                    column_config={
                        "annual_return": st.column_config.NumberColumn(
                            "Rendimento", format="percent"
                        ),
                        "annual_volatility": st.column_config.NumberColumn(
                            "Volatilità", format="percent"
                        ),
                        "sharpe": st.column_config.NumberColumn("Sharpe", format="%.2f"),
                    },
                )
                st.markdown("**Pesi suggeriti**")
                st.dataframe(
                    pd.DataFrame(candidates),
                    column_config={
                        c: st.column_config.NumberColumn(c, format="percent")
                        for c in candidates
                    },
                )

# ---------------------------------------------------------------- correlazioni
with tab_corr:
    st.subheader("Quali titoli si muovono insieme")
    st.caption(
        "Correlazione dei rendimenti giornalieri: **+1** = si muovono identici, "
        "**0** = indipendenti, **-1** = opposti."
    )

    all_prices = load_market_db()
    if all_prices is None:
        st.info(
            "Serve il database Nasdaq-100: esegui `python download_nasdaq100.py` dal terminale."
        )
    else:
        col_sel, col_per = st.columns([2, 1])
        with col_sel:
            corr_ticker = st.selectbox(
                "Titolo di riferimento", sorted(all_prices.columns), index=None,
                placeholder="Scegli un titolo del Nasdaq-100...",
            )
        with col_per:
            corr_period = st.selectbox("Periodo", list(PERIOD_DAYS), index=2, key="corr_period")

        if corr_ticker:
            cutoff = all_prices.index[-1] - pd.Timedelta(days=PERIOD_DAYS[corr_period])
            window_returns = compute_daily_returns(all_prices.loc[all_prices.index >= cutoff])
            min_periods = max(15, min(60, len(window_returns) // 2))
            corr = correlations_with(window_returns, corr_ticker, min_periods=min_periods)

            col_top, col_bottom = st.columns(2, gap="large")
            with col_top:
                st.markdown(f"**Si muovono INSIEME a {corr_ticker}**")
                st.altair_chart(correlation_bars(corr.head(10)), use_container_width=True)
            with col_bottom:
                st.markdown(f"**Si muovono in modo INDIPENDENTE o OPPOSTO a {corr_ticker}**")
                st.altair_chart(
                    correlation_bars(corr.tail(10).sort_values()), use_container_width=True
                )

    if computed is not None and len(amounts) >= 2:
        st.divider()
        st.subheader("Diversificazione del tuo portafoglio")
        pf_corr = correlation_matrix(computed["returns"], min_periods=computed["min_periods"])
        avg_corr = computed["avg_corr"]

        pairs = pf_corr.where(
            pd.DataFrame(
                [[i < j for j in range(len(pf_corr))] for i in range(len(pf_corr))],
                index=pf_corr.index, columns=pf_corr.columns,
            )
        ).stack()

        col_metric, col_heat = st.columns([1, 2], gap="large")
        with col_metric:
            st.metric("Correlazione media", f"{avg_corr:.2f}")
            if avg_corr > 0.6:
                st.warning("I tuoi titoli si muovono molto insieme.")
            elif avg_corr > 0.3:
                st.info("Diversificazione nella media.")
            else:
                st.success("Buona diversificazione.")
            if len(pairs):
                tightest = pairs.idxmax()
                st.caption(
                    f"Coppia più legata: **{tightest[0]} – {tightest[1]}** ({pairs.max():+.2f})"
                )
        with col_heat:
            st.altair_chart(correlation_heatmap(pf_corr), use_container_width=True)

# ---------------------------------------------------------------- fondamentali
with tab_fundamentals:
    st.subheader("Ricavi, margini, debito, crescita e multipli")

    default_tickers = " ".join(sorted(amounts)) if amounts else "AAPL MSFT NVDA"
    tickers_text = st.text_input("Ticker separati da spazio", default_tickers)
    fund_tickers = tuple(t.upper() for t in tickers_text.split())

    if fund_tickers:
        try:
            data = cached_fundamentals(fund_tickers)
            st.dataframe(
                data,
                column_config={
                    "name": st.column_config.TextColumn("Nome"),
                    "revenue": st.column_config.NumberColumn("Ricavi (TTM)", format="compact"),
                    "net_income": st.column_config.NumberColumn(
                        "Utile netto (TTM)", format="compact"
                    ),
                    "gross_margin": st.column_config.NumberColumn(
                        "Margine lordo", format="percent"
                    ),
                    "operating_margin": st.column_config.NumberColumn(
                        "Margine operativo", format="percent"
                    ),
                    "net_margin": st.column_config.NumberColumn("Margine netto", format="percent"),
                    "total_debt": st.column_config.NumberColumn("Debito", format="compact"),
                    "debt_to_equity": st.column_config.NumberColumn("Debito/Equity", format="%.1f"),
                    "revenue_growth": st.column_config.NumberColumn(
                        "Crescita ricavi", format="percent"
                    ),
                    "earnings_growth": st.column_config.NumberColumn(
                        "Crescita utili", format="percent"
                    ),
                    "pe": st.column_config.NumberColumn("P/E", format="%.1f"),
                    "forward_pe": st.column_config.NumberColumn("P/E fwd", format="%.1f"),
                    "ev_ebitda": st.column_config.NumberColumn("EV/EBITDA", format="%.1f"),
                    "ps": st.column_config.NumberColumn("P/S", format="%.1f"),
                },
            )

            st.divider()
            st.markdown("#### 🧬 Scheda titolo")
            card_ticker = st.selectbox("Titolo", list(data.index))
            row = data.loc[card_ticker]
            card_prices = cached_prices((card_ticker,), "1y")
            card_vol = float(
                compute_daily_returns(card_prices)[card_ticker].std() * TRADING_DAYS**0.5
            )
            scores = stock_scores(row, card_vol)
            overall = scores.pop("Overall")

            col_card, col_num = st.columns([2, 1], gap="large")
            with col_card:
                st.markdown(
                    dna_card_html(scores, f"{row['name']}"), unsafe_allow_html=True
                )
            with col_num:
                st.metric(
                    "Punteggio complessivo",
                    f"{overall:.0f}/100",
                    help="Media pesata: Growth 35%, Quality 35%, Valuation 20%, "
                    "basso rischio 10%. Euristica, non un consiglio d'investimento.",
                )
                st.caption(f"Volatilità annua: {card_vol:.0%}")
        except ValueError as exc:
            st.error(f"{exc}")

# ---------------------------------------------------------------- nasdaq-100
with tab_nasdaq:
    st.subheader("I 103 componenti del Nasdaq-100 a confronto")

    all_prices = load_market_db()
    if all_prices is None:
        st.info(
            "Database non ancora scaricato: esegui `python download_nasdaq100.py` dal terminale."
        )
    else:
        ndx_period = st.selectbox("Periodo di confronto", list(PERIOD_DAYS), index=2)
        cutoff = all_prices.index[-1] - pd.Timedelta(days=PERIOD_DAYS[ndx_period])
        window = all_prices.loc[all_prices.index >= cutoff]

        stats = pd.DataFrame(
            {
                "period_return": per_ticker_cumulative_return(window),
                "annual_volatility": compute_daily_returns(window).std() * TRADING_DAYS**0.5,
            }
        ).rename_axis("ticker").reset_index()

        col_scatter, col_table = st.columns([3, 2], gap="large")
        with col_scatter:
            st.markdown(f"**Rischio vs rendimento ({ndx_period})** — ogni punto è un titolo")
            st.scatter_chart(
                stats,
                x="annual_volatility",
                y="period_return",
                x_label="Volatilità annualizzata",
                y_label=f"Rendimento cumulato ({ndx_period})",
                color=PALETTE[0],
                height=420,
            )
        with col_table:
            st.markdown("**Classifica completa**")
            st.dataframe(
                stats.sort_values("period_return", ascending=False),
                column_config={
                    "ticker": st.column_config.TextColumn("Ticker"),
                    "period_return": st.column_config.NumberColumn(
                        f"Rendimento ({ndx_period})", format="percent"
                    ),
                    "annual_volatility": st.column_config.NumberColumn(
                        "Volatilità annua", format="percent"
                    ),
                },
                hide_index=True,
                height=420,
            )
        st.caption(
            "Rendimento cumulato nel periodo selezionato. "
            "Aggiorna i dati con `python download_nasdaq100.py`."
        )

# ---------------------------------------------------------------- backtest
with tab_backtest:
    st.subheader("E se avessi seguito una strategia?")
    st.caption(
        "Ribilanciamento trimestrale, pesi calcolati solo sui dati precedenti "
        "(nessuno sguardo al futuro). Limiti: niente costi di transazione, e "
        "l'universo usa i componenti ATTUALI del Nasdaq-100 (survivorship bias)."
    )

    all_prices = load_market_db()
    if all_prices is None:
        st.info(
            "Serve il database Nasdaq-100: esegui `python download_nasdaq100.py` dal terminale."
        )
    else:
        options = ["Equipesato Nasdaq-100", "Momentum (top 10 a 6 mesi)"]
        if len(amounts) >= 2:
            options += [
                "Il tuo portafoglio (buy & hold)",
                "Massimo Sharpe sui tuoi titoli",
                "Minima varianza sui tuoi titoli",
            ]
        chosen = st.multiselect(
            "Strategie da confrontare", options, default=options[:2]
        )

        bt_years = st.select_slider("Orizzonte", ["1 anno", "2 anni", "5 anni"], "5 anni")
        cutoff = all_prices.index[-1] - pd.Timedelta(days=PERIOD_DAYS[bt_years])
        window = all_prices.loc[all_prices.index >= cutoff]

        if chosen:
            with st.spinner("Eseguo i backtest..."):
                curves = {}
                try:
                    if "Equipesato Nasdaq-100" in chosen:
                        curves["Equipesato Nasdaq-100"] = run_backtest(window, equal_weight)
                    if "Momentum (top 10 a 6 mesi)" in chosen:
                        curves["Momentum (top 10 a 6 mesi)"] = run_backtest(
                            window, lambda w: momentum_top(w, top_n=10)
                        )
                    if len(amounts) >= 2:
                        my_tickers = [t for t in sorted(amounts) if t in window.columns]
                        my_prices = (
                            window[my_tickers]
                            if len(my_tickers) == len(amounts)
                            else cached_prices(
                                tuple(sorted(amounts)),
                                {"1 anno": "1y", "2 anni": "2y", "5 anni": "5y"}[bt_years],
                            )
                        )
                        weights_now = pd.Series(amounts) / sum(amounts.values())
                        if "Il tuo portafoglio (buy & hold)" in chosen:
                            curves["Il tuo portafoglio (buy & hold)"] = buy_and_hold(
                                my_prices, weights_now
                            )
                        if "Massimo Sharpe sui tuoi titoli" in chosen:
                            curves["Massimo Sharpe sui tuoi titoli"] = run_backtest(
                                my_prices, max_sharpe
                            )
                        if "Minima varianza sui tuoi titoli" in chosen:
                            curves["Minima varianza sui tuoi titoli"] = run_backtest(
                                my_prices, min_variance
                            )
                except ValueError as exc:
                    st.error(f"{exc}")

            if curves:
                equity = pd.DataFrame(curves).dropna(how="all")
                cols = st.columns(len(curves))
                for col, (name, curve) in zip(cols, curves.items()):
                    col.metric(name, f"{curve.iloc[-1] / 100 - 1:+.0%}")
                st.line_chart(equity, color=PALETTE[: len(curves)], height=380)
                st.caption("Curve a base 100 all'inizio dell'orizzonte scelto.")
