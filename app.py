"""Portfolio Intelligence — il check-up onesto del portafoglio in 60 secondi.

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
from src.analytics.factors import composite_scores, multifactor_weights
from src.analytics.insights import (
    dna_label,
    dna_scores,
    equal_weight_portfolio,
    find_opportunities,
    find_problems,
    generate_insights,
    generate_suggestions,
    monthly_returns,
    portfolio_health_score,
    portfolio_risk_score,
    radar_scores,
    reduce_position,
    risk_contributions,
    stock_scores,
)
from src.analytics.performance import (
    annualized_geometric_return,
    annualized_sharpe,
    beta_alpha,
    max_drawdown,
    sortino_ratio,
    value_at_risk,
)
from src.analytics.simulation import simulate_shock
from src.data.cache import load_nasdaq100_prices
from src.data.fx import convert_to_eur, fetch_eurusd
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
    GAIN,
    LOSS,
    PALETTE,
    allocation_bars,
    benchmark_overlay,
    contribution_bars,
    correlation_bars,
    correlation_heatmap,
    efficient_frontier_chart,
    equity_area,
    galaxy_chart,
    monthly_bars,
    radar_chart,
    returns_histogram,
    simple_line,
    underwater_chart,
    weight_vs_risk_bars,
)
from src.visualization.pdf_report import build_report

BENCHMARK = "QQQ"  # ETF sul Nasdaq-100
TRADING_DAYS = 252
PERIOD_DAYS = {"1 mese": 30, "6 mesi": 182, "1 anno": 365, "2 anni": 730, "5 anni": 1826}
AMBER = "#f7a600"

st.set_page_config(
    page_title="Portfolio Intelligence", page_icon="📈", layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------- design system
st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Space+Grotesk:wght@500;600;700&display=swap');

    :root {{
        --panel: #12161e;
        --line: rgba(255, 255, 255, 0.07);
        --muted: #8b93a3;
        --accent: {AMBER};
        --gain: {GAIN};
        --loss: {LOSS};
        --font-ui: 'Inter', -apple-system, 'Segoe UI', sans-serif;
        --font-display: 'Space Grotesk', 'Inter', sans-serif;
    }}
    html, body, p, div, span, label, input, button, textarea, select, li {{
        font-family: var(--font-ui) !important;
    }}
    code, pre {{ font-family: ui-monospace, 'SF Mono', Menlo, monospace !important; }}
    [data-testid="stIconMaterial"], [class*="material-symbols"] {{
        font-family: 'Material Symbols Rounded' !important;
    }}
    .block-container {{ padding-top: 1.1rem; max-width: 1320px; }}
    h1, h2, h3 {{
        font-family: var(--font-display) !important; letter-spacing: -0.01em;
    }}

    /* ---- barra superiore ---- */
    .topbar {{
        display: flex; justify-content: space-between; align-items: baseline;
        padding: 2px 2px 10px;
    }}
    .brand {{
        font-family: var(--font-display) !important;
        font-size: 1.02rem; letter-spacing: 0.14em; color: #e6e8ee;
        text-transform: uppercase; font-weight: 500;
    }}
    .brand b {{ color: var(--accent); font-weight: 700; }}
    .brand-tag {{ font-size: 0.72rem; color: var(--muted); letter-spacing: 0.04em; }}

    /* ---- menu di navigazione (segmented control) ---- */
    .st-key-nav [data-testid="stSegmentedControl"] button,
    .st-key-nav [role="radiogroup"] button {{
        background: transparent !important;
        border: none !important;
        border-radius: 0 !important;
        border-bottom: 2px solid transparent !important;
        padding: 6px 14px 10px !important;
    }}
    .st-key-nav button p {{
        font-size: 0.78rem !important; font-weight: 600;
        letter-spacing: 0.07em; text-transform: uppercase;
        color: var(--muted) !important;
    }}
    .st-key-nav button[aria-checked="true"],
    .st-key-nav button[kind="segmented_controlActive"] {{
        border-bottom-color: var(--accent) !important;
    }}
    .st-key-nav button[aria-checked="true"] p,
    .st-key-nav button[kind="segmented_controlActive"] p {{
        color: #ffffff !important;
    }}
    .st-key-nav {{ border-bottom: 1px solid var(--line); }}

    /* ---- metriche flat: niente scatole, solo numeri e separatori ---- */
    .panel {{
        background: var(--panel); border: 1px solid var(--line);
        border-radius: 12px; padding: 20px 24px; height: 100%;
    }}
    [data-testid="stMetric"] {{
        background: transparent; border: none;
        border-left: 2px solid var(--line);
        border-radius: 0; padding: 2px 0 2px 14px;
    }}
    [data-testid="stMetricLabel"] p {{
        font-size: 0.68rem !important; text-transform: uppercase;
        letter-spacing: 0.1em; color: var(--muted) !important; font-weight: 600;
    }}
    [data-testid="stMetricValue"] {{
        font-family: var(--font-ui) !important; font-weight: 700;
        font-variant-numeric: tabular-nums; font-size: 1.65rem;
        letter-spacing: -0.02em;
    }}
    [data-testid="stMetricDelta"] {{
        font-variant-numeric: tabular-nums; font-size: 0.85rem; font-weight: 600;
    }}

    /* ---- etichette di sezione ---- */
    .sec {{
        display: flex; align-items: center; gap: 10px;
        font-size: 0.72rem; font-weight: 700; letter-spacing: 0.09em;
        text-transform: uppercase; color: var(--muted);
        margin: 26px 0 10px;
    }}
    .sec::before {{
        content: ""; display: block; width: 3px; height: 14px;
        background: var(--accent); border-radius: 2px;
    }}

    /* ---- hero con gauge ---- */
    .hero-panel {{
        display: flex; align-items: center; gap: 28px;
        background: var(--panel); border: 1px solid var(--line);
        border-radius: 12px; padding: 22px 28px;
    }}
    .gauge {{
        width: 128px; height: 128px; border-radius: 50%; flex-shrink: 0;
        background: conic-gradient(var(--gcol) calc(var(--val) * 3.6deg),
                                   rgba(255,255,255,0.07) 0);
        display: flex; align-items: center; justify-content: center;
    }}
    .gauge-inner {{
        width: 102px; height: 102px; border-radius: 50%; background: var(--panel);
        display: flex; flex-direction: column; align-items: center;
        justify-content: center;
    }}
    .gauge-num {{
        font-family: var(--font-display) !important;
        font-size: 2.2rem; font-weight: 700;
        line-height: 1; color: var(--gcol);
    }}
    .gauge-sub {{ font-size: 0.64rem; color: var(--muted); letter-spacing: 0.12em; }}
    .hero-meta .label {{
        font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.1em;
        color: var(--muted); font-weight: 600;
    }}
    .hero-meta .big {{
        font-family: var(--font-display) !important;
        font-size: 2.5rem; font-weight: 700; letter-spacing: -0.02em;
        font-variant-numeric: tabular-nums; margin: 2px 0;
    }}
    .chg {{
        font-size: 1rem; font-weight: 700; font-variant-numeric: tabular-nums;
    }}
    .up {{ color: var(--gain); }}
    .down {{ color: var(--loss); }}

    /* ---- DNA card ---- */
    .dna-title {{
        font-size: 0.72rem; letter-spacing: 0.16em; color: var(--muted);
        font-weight: 700; margin-bottom: 14px;
    }}
    .dna-row {{ display: flex; align-items: center; margin: 9px 0; gap: 10px; }}
    .dna-name {{ width: 72px; font-size: 0.86rem; color: #c5cad6; }}
    .dna-track {{
        flex: 1; background: rgba(255,255,255,0.07); border-radius: 4px; height: 6px;
    }}
    .dna-fill {{ height: 100%; border-radius: 4px; background: #3987e5; }}
    .dna-fill.risk {{ background: var(--accent); }}
    .dna-value {{
        width: 36px; text-align: right; font-size: 0.88rem; font-weight: 700;
        font-variant-numeric: tabular-nums;
    }}
    .dna-status {{ margin-top: 14px; font-weight: 600; font-size: 0.98rem; }}

    .ai-card p {{ margin: 0 0 10px; line-height: 1.55; font-size: 0.95rem; }}

    /* ---- sidebar ---- */
    [data-testid="stSidebar"] {{
        background: #0d1117; border-right: 1px solid var(--line);
    }}
    [data-testid="stSidebar"] .sec {{ margin: 10px 0 6px; }}
    [data-testid="stSidebar"] hr {{ margin: 12px 0; }}

    /* ---- bottoni ed expander ---- */
    .stButton button, .stDownloadButton button {{
        border-radius: 8px; border: 1px solid rgba(255,255,255,0.12);
    }}
    [data-testid="stExpander"] {{
        border: 1px solid var(--line); border-radius: 10px; background: transparent;
    }}
    header[data-testid="stHeader"] {{ background: transparent; }}
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


@st.cache_data(ttl=3600, show_spinner="Scarico il cambio EUR/USD...")
def cached_eurusd(period: str) -> pd.Series:
    return fetch_eurusd(period)


def eur(value: float) -> str:
    return f"{value:,.0f} €".replace(",", ".")


def sec(title: str) -> None:
    st.markdown(f'<div class="sec">{title}</div>', unsafe_allow_html=True)


@st.cache_data(ttl=600, show_spinner=False)
def _cached_market_db(_mtime: float | None) -> pd.DataFrame | None:
    # _mtime nel cache key: il DB aggiornato invalida la cache
    prices = load_stored_prices()
    if prices is not None:
        return prices
    return load_nasdaq100_prices()


def load_market_db() -> pd.DataFrame | None:
    from src.data.store import DB_PATH

    mtime = DB_PATH.stat().st_mtime if DB_PATH.exists() else None
    return _cached_market_db(mtime)


def market_db_required(view_key: str) -> pd.DataFrame | None:
    """Il database prezzi, con download integrato se assente (per il cloud)."""
    prices = load_market_db()
    if prices is None:
        st.info(
            "Il database Nasdaq-100 (5 anni di prezzi giornalieri per 103 titoli) "
            "non è ancora presente."
        )
        if st.button("⬇️ Scarica ora (~1 minuto)", key=f"dl_{view_key}", type="primary"):
            from download_nasdaq100 import update_nasdaq100

            with st.spinner("Scarico 5 anni di prezzi da Yahoo Finance..."):
                update_nasdaq100()
            st.rerun()
    return prices


def dna_card_html(dna: dict[str, float], label: str, title: str = "PORTFOLIO DNA") -> str:
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
        f'<div class="panel"><div class="dna-title">{title}</div>{rows}'
        f'<div class="dna-status">{label}</div></div>'
    )


def hero_html(health: int, value: str, change: float, period: str) -> str:
    gauge_color = GAIN if health >= 67 else AMBER if health >= 34 else LOSS
    arrow, css = ("▲", "up") if change >= 0 else ("▼", "down")
    return f"""
    <div class="hero-panel" style="--val:{health}; --gcol:{gauge_color}">
      <div class="gauge"><div class="gauge-inner">
        <span class="gauge-num">{health}</span>
        <span class="gauge-sub">HEALTH /100</span>
      </div></div>
      <div class="hero-meta">
        <div class="label">Valore stimato</div>
        <div class="big">{value}</div>
        <div class="chg {css}">{arrow} {change:+.1%} · {period}</div>
      </div>
    </div>"""


# ================================================================ SIDEBAR
with st.sidebar:
    st.markdown(
        '<div class="brand" style="font-size:.9rem">◆ PORTFOLIO <b>INTELLIGENCE</b></div>',
        unsafe_allow_html=True,
    )
    sec("Il tuo portafoglio")
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
        width="stretch",
    )
    with st.expander("📂 Importa da CSV/Excel"):
        uploaded = st.file_uploader(
            "Estratto del broker (ticker + importo)", type=["csv", "xlsx", "xls"]
        )
    saved = list_portfolios()
    with st.expander("💾 Portafogli salvati"):
        selected_saved = st.selectbox(
            "Carica", ["— usa l'editor —"] + sorted(saved), index=0
        )
        portfolio_name = st.text_input("Nome", value="Il mio portafoglio")
        want_save = st.button("Salva composizione attiva", width="stretch")
    with st.expander("⚙️ Impostazioni"):
        period = st.selectbox(
            "Orizzonte storico", ["1mo", "6mo", "1y", "2y", "5y"], index=2, key="pf_period"
        )
        in_eur = st.toggle(
            "💱 Misura tutto in euro",
            value=True,
            help="I titoli USA quotano in dollari: convertendo in EUR le metriche "
            "includono anche le oscillazioni EUR/USD, il rischio reale di un "
            "investitore europeo.",
        )
        risk_free = st.number_input(
            "Tasso risk-free annuo (%)",
            min_value=0.0, max_value=10.0, value=3.0, step=0.25,
            help="Rendimento senza rischio usato in Sharpe, Sortino e ottimizzazione.",
        ) / 100

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
        st.caption(f"⚡ Attivo: {source}")
    if want_save and amounts:
        save_portfolio(portfolio_name, amounts)
        st.toast(f"Portafoglio «{portfolio_name}» salvato ✓")

    total = sum(amounts.values())
    if total:
        st.caption(f"Totale investito: **{eur(total)}** · {len(amounts)} titoli")

portfolio = (
    [{"ticker": t, "weight": amount / total} for t, amount in amounts.items()] if total else []
)

# ================================================================ CALCOLI CONDIVISI
computed: dict | None = None
compute_error: str | None = None
if portfolio:
    try:
        tickers = tuple(sorted(amounts))
        prices = cached_prices(tickers, period)
        bench_prices = cached_prices((BENCHMARK,), period)
        if in_eur:
            eurusd = cached_eurusd(period)
            prices = convert_to_eur(prices, eurusd)
            bench_prices = convert_to_eur(bench_prices, eurusd)
        returns = compute_daily_returns(prices)

        pf_daily = portfolio_daily_returns(returns, portfolio)
        pf_value = (1 + pf_daily).cumprod()
        cum_return = float(pf_value.iloc[-1] - 1)

        annual_ret = annualized_geometric_return(pf_daily)
        annual_vol = portfolio_volatility(returns, portfolio) * TRADING_DAYS**0.5
        drawdown = max_drawdown(pf_value)
        var_95 = value_at_risk(pf_daily)
        min_periods = max(15, min(60, len(returns) // 2))
        avg_corr = average_pairwise_correlation(returns, min_periods=min_periods)

        bench_daily = compute_daily_returns(bench_prices)[BENCHMARK]
        beta, alpha = beta_alpha(pf_daily, bench_daily)

        contributions = risk_contributions(returns, portfolio)
        radar = radar_scores(annual_vol, portfolio, drawdown, avg_corr)
        risk_score = portfolio_risk_score(radar)

        fund = cached_fundamentals(tickers)
        dna = dna_scores(fund, portfolio, annual_vol, avg_corr)
        health = portfolio_health_score(dna, radar)

        computed = {
            "returns": returns, "prices": prices, "pf_daily": pf_daily,
            "pf_value": pf_value, "bench_daily": bench_daily,
            "annual_ret": annual_ret, "annual_vol": annual_vol,
            "drawdown": drawdown, "avg_corr": avg_corr, "var_95": var_95,
            "beta": beta, "alpha": alpha, "min_periods": min_periods,
            "cum_return": cum_return, "risk_score": risk_score,
            "contributions": contributions, "radar": radar, "fund": fund,
            "dna": dna, "health": health,
        }
    except ValueError as exc:
        compute_error = str(exc)

# ================================================================ HEADER + NAV
st.markdown(
    f"""<div class="topbar">
    <span class="brand">◆ PORTFOLIO <b>INTELLIGENCE</b></span>
    <span class="brand-tag">{"EUR · cambio incluso" if in_eur else "valute originali"}
    · dati Yahoo Finance</span></div>""",
    unsafe_allow_html=True,
)
with st.container(key="nav"):
    view = st.segmented_control(
        "Sezione",
        ["Check-up", "Analisi", "Visual", "Ottimizza", "Correlazioni",
         "Fondamentali", "Mercato", "Backtest"],
        default="Check-up",
        label_visibility="collapsed",
    )
view = view or "Check-up"

if compute_error:
    st.error(compute_error)

NEEDS_PORTFOLIO = {"Check-up", "Analisi", "Visual", "Ottimizza"}
if view in NEEDS_PORTFOLIO and computed is None:
    if not compute_error:
        st.info("⬅ Inserisci almeno un titolo con un importo nella barra laterale.")

# ================================================================ CHECK-UP
elif view == "Check-up":
    c = computed
    col_hero, col_equity = st.columns([1, 1.4], gap="large")
    with col_hero:
        st.markdown(
            hero_html(c["health"], eur(total * (1 + c["cum_return"])),
                      c["cum_return"], period),
            unsafe_allow_html=True,
        )
        st.caption(
            "Health Score: 40% basso rischio, 30% qualità dei bilanci, "
            "15% valutazioni, 15% diversificazione."
        )
        if c["dna"]:
            st.markdown(f"**{dna_label(c['dna'])}**")
    with col_equity:
        sec(f"Andamento del capitale ({period})")
        st.altair_chart(
            equity_area(total * (1 + c["pf_daily"]).cumprod(), total),
            width="stretch",
        )
        st.caption("Linea tratteggiata = capitale investito oggi, proiettato indietro.")

    sec("Le tue posizioni")
    cum_by_ticker = per_ticker_cumulative_return(c["prices"])
    normalized_pos = c["prices"] / c["prices"].apply(lambda s: s.dropna().iloc[0])
    position_rows = [
        {
            "Titolo": t,
            "Importo": amounts[t],
            "Peso": amounts[t] / total,
            "Rendimento": cum_by_ticker.get(t),
            "Andamento": normalized_pos[t].dropna().tolist()[-130:],
        }
        for t in sorted(amounts, key=amounts.get, reverse=True)
    ]
    st.dataframe(
        pd.DataFrame(position_rows),
        column_config={
            "Titolo": st.column_config.TextColumn("Titolo"),
            "Importo": st.column_config.NumberColumn("Importo", format="%.0f €"),
            "Peso": st.column_config.NumberColumn("Peso", format="percent"),
            "Rendimento": st.column_config.NumberColumn(
                f"Rendimento ({period})", format="percent"
            ),
            "Andamento": st.column_config.AreaChartColumn(
                f"Andamento ({period})", width="medium"
            ),
        },
        hide_index=True,
        width="stretch",
    )

    sec("I problemi principali")
    problems = find_problems(portfolio, c["fund"], c["contributions"],
                             c["avg_corr"], c["radar"])
    session_alerts = [
        a for a in evaluate_alerts(c["returns"], portfolio, c["contributions"],
                                   c["avg_corr"], c["drawdown"])
        if "Ultima seduta" in a
    ]
    top_problems = (session_alerts + problems)[:5]
    if top_problems:
        for problem in top_problems:
            st.markdown(problem)
    else:
        st.success("Nessun problema rilevato dalle regole monitorate ✓")

    sec("Il tuo rischio, in euro")
    r1, r2, r3 = st.columns(3)
    r1.metric(
        "Oscillazione tipica in 1 anno",
        f"± {eur(total * c['annual_vol'])}",
        delta=f"{c['annual_vol']:.1%}", delta_color="off",
        help="Un anno normale può chiudersi con uno scarto di questa entità "
        "in più o in meno (1 deviazione standard).",
    )
    r2.metric(
        "In una giornata nera (VaR 95%)",
        eur(total * c["var_95"]),
        help="Nel 95% dei giorni non perdi più di questa cifra. Stima storica.",
    )
    r3.metric(
        "Nella peggior discesa del periodo",
        eur(total * c["drawdown"]),
        delta=f"{c['drawdown']:.1%}", delta_color="off",
        help="Quanto avresti visto scendere il portafoglio dal picco (max drawdown).",
    )
    st.caption("Stime dall'andamento storico del periodo: non sono una previsione.")

    sec("Cosa puoi fare (simulato sui tuoi dati)")

    def simulate_change(new_pf: list) -> tuple[float, int]:
        new_vol = portfolio_volatility(c["returns"], new_pf) * TRADING_DAYS**0.5
        new_daily = portfolio_daily_returns(c["returns"], new_pf)
        new_dd = max_drawdown((1 + new_daily).cumprod())
        new_radar = radar_scores(new_vol, new_pf, new_dd, c["avg_corr"])
        new_dna = dna_scores(c["fund"], new_pf, new_vol, c["avg_corr"])
        return new_vol, portfolio_health_score(new_dna, new_radar)

    weights_sorted = sorted(portfolio, key=lambda p: -p["weight"])
    candidates_sim = {}
    if len(portfolio) >= 2 and weights_sorted[0]["weight"] > 0.25:
        top_t = weights_sorted[0]["ticker"]
        candidates_sim[f"Se dimezzi {top_t} (redistribuendo sugli altri)"] = (
            reduce_position(portfolio, top_t, 0.5)
        )
    if len(portfolio) >= 3 and c["radar"].get("Concentrazione", 0) > 25:
        candidates_sim["Se equipesassi tutti i titoli"] = equal_weight_portfolio(portfolio)

    simulations, discarded = [], []
    for name, new_pf in candidates_sim.items():
        new_vol, new_health = simulate_change(new_pf)
        improves = new_health > c["health"] or (
            new_health == c["health"] and new_vol < c["annual_vol"] * 0.98
        )
        text = (
            f"**{name}**: oscillazione annua da ± {eur(total * c['annual_vol'])} "
            f"a ± {eur(total * new_vol)}, Health Score da {c['health']} "
            f"a **{new_health}**."
        )
        (simulations if improves else discarded).append(text)

    for simulation in simulations:
        st.markdown("✅ " + simulation)
    if not simulations and candidates_sim:
        st.markdown(
            "Abbiamo simulato le mosse più ovvie sui tuoi dati, ma **nessuna "
            "migliora il profilo attuale** — un buon segno per come sei pesato:"
        )
        for text in discarded:
            st.caption("✗ " + text)
    for opportunity in find_opportunities(portfolio, c["fund"])[:2]:
        st.markdown(opportunity)
    if not candidates_sim:
        st.caption("Nessuna simulazione proposta: i pesi sono già ben distribuiti.")

    st.divider()
    col_pdf, col_log, col_hist = st.columns([1.2, 1, 1.8], gap="large")
    with col_pdf:
        insights = generate_insights(
            period, c["cum_return"], c["contributions"], c["avg_corr"],
            c["drawdown"], c["beta"], BENCHMARK,
        )
        report_metrics = {
            "Sharpe ratio": f"{annualized_sharpe(c['returns'], portfolio, risk_free_rate=risk_free):.2f}",
            "Sortino ratio": f"{sortino_ratio(c['returns'], portfolio, risk_free_rate=risk_free):.2f}",
            "Oscillazione annua": f"± {eur(total * c['annual_vol'])}",
            "VaR 95% (1 giorno)": eur(total * c["var_95"]),
            "Perdita massima storica": f"{c['drawdown']:.1%}",
            f"Beta vs {BENCHMARK}": f"{c['beta']:.2f}",
            "Correlazione media": f"{c['avg_corr']:.2f}",
            "Tasso risk-free usato": f"{risk_free:.2%}",
        }
        st.download_button(
            "📄 Scarica il report PDF",
            data=build_report(
                portfolio_name=portfolio_name,
                positions=amounts,
                period=period,
                cum_return=c["cum_return"],
                health_score=c["health"],
                metrics=report_metrics,
                insights=insights + top_problems,
                suggestions=simulations
                + generate_suggestions(c["dna"], c["radar"], c["contributions"])
                + find_opportunities(portfolio, c["fund"]),
            ),
            file_name=f"portfolio_report_{pd.Timestamp.now():%Y%m%d}.pdf",
            mime="application/pdf",
            width="stretch",
            type="primary",
        )
    with col_log:
        if st.button("📝 Salva nello storico", width="stretch"):
            log_analysis(portfolio_name, period, total, c["cum_return"], c["risk_score"])
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

# ================================================================ ANALISI
elif view == "Analisi":
    c = computed
    sharpe = annualized_sharpe(c["returns"], portfolio, risk_free_rate=risk_free)
    sortino = sortino_ratio(c["returns"], portfolio, risk_free_rate=risk_free)

    sec("Rendimento")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Investimento", eur(total))
    m2.metric(
        "Rendimento annualizzato (composto)",
        eur(total * c["annual_ret"]),
        delta=f"{c['annual_ret']:+.1%}",
        help="CAGR del periodo osservato: non sovrastima in presenza di volatilità.",
    )
    m3.metric(
        "Sharpe ratio", f"{sharpe:.2f}",
        help=f"Rendimento extra per unità di rischio (risk-free {risk_free:.1%}): "
        "sopra 1 è buono, sopra 2 ottimo.",
    )
    m4.metric(
        "Sortino ratio", f"{sortino:.2f}",
        help="Come lo Sharpe ma penalizza solo la volatilità al ribasso.",
    )

    sec("Rischio")
    r1, r2, r3, r4 = st.columns(4)
    r1.metric(
        "Oscillazione tipica in 1 anno",
        f"± {eur(total * c['annual_vol'])}",
        delta=f"{c['annual_vol']:.1%}", delta_color="off",
    )
    r2.metric("Perdita massima storica", f"{c['drawdown']:.1%}")
    r3.metric("VaR 95% (1 giorno)", eur(total * c["var_95"]))
    r4.metric(
        f"Beta vs {BENCHMARK}", f"{c['beta']:.2f}",
        delta=f"α {c['alpha']:+.1%}/anno", delta_color="off",
    )
    st.caption("Stime basate sull'andamento storico: non sono una previsione.")

    sec(f"Portafoglio vs Nasdaq-100 ({BENCHMARK}) · base 100")
    bench_value = (1 + c["bench_daily"]).cumprod()
    st.altair_chart(
        benchmark_overlay(c["pf_value"], bench_value, BENCHMARK),
        width="stretch",
    )
    excess = c["cum_return"] - float(bench_value.iloc[-1] - 1)
    st.caption(
        f"Nel periodo hai fatto **{excess:+.1%}** rispetto al Nasdaq-100"
        + (" (al netto del cambio EUR/USD)." if in_eur else ".")
    )

    col_dd, col_hist = st.columns(2, gap="large")
    with col_dd:
        sec("Quanto sotto il massimo (drawdown)")
        st.altair_chart(underwater_chart(c["pf_value"]), width="stretch")
        st.caption(
            "Ogni discesa sotto lo zero è tempo passato in perdita rispetto "
            "al picco precedente."
        )
    with col_hist:
        sec("Distribuzione dei giorni")
        st.altair_chart(
            returns_histogram(c["pf_daily"], c["var_95"]), width="stretch"
        )
        st.caption(
            "Ogni barra conta i giorni con quel rendimento. La linea rossa è il "
            "VaR 95%: solo il 5% dei giorni è andato peggio."
        )

    if len(c["pf_daily"]) >= 80:
        col_rvol, col_rbeta = st.columns(2, gap="large")
        with col_rvol:
            sec("Volatilità annualizzata · rolling 60 giorni")
            rolling_vol = (c["pf_daily"].rolling(60).std() * TRADING_DAYS**0.5).dropna()
            st.altair_chart(simple_line(rolling_vol), width="stretch")
            st.caption("Come è cambiata la rischiosità del portafoglio nel tempo.")
        with col_rbeta:
            sec(f"Beta vs {BENCHMARK} · rolling 60 giorni")
            aligned = pd.concat(
                {"pf": c["pf_daily"], "bench": c["bench_daily"]}, axis=1
            ).dropna()
            rolling_beta = (
                aligned["pf"].rolling(60).cov(aligned["bench"])
                / aligned["bench"].rolling(60).var()
            ).dropna()
            st.altair_chart(
                simple_line(rolling_beta, color=PALETTE[0], y_format=".1f"),
                width="stretch",
            )
            st.caption("Sopra 1 amplifichi il mercato, sotto 1 lo attenui.")

    col_contrib, col_alloc = st.columns([1.3, 1], gap="large")
    with col_contrib:
        sec("Chi ha fatto il risultato (in euro)")
        cum_by_ticker = per_ticker_cumulative_return(c["prices"])
        contributions_eur = pd.Series(
            {
                t: amounts[t] * float(cum_by_ticker.get(t, 0.0))
                for t in amounts
            }
        )
        st.altair_chart(contribution_bars(contributions_eur), width="stretch")
        st.caption(
            "Importo investito × rendimento del titolo (pesi costanti): "
            "la somma ricostruisce circa il risultato totale."
        )
    with col_alloc:
        sec("Distribuzione")
        st.altair_chart(allocation_bars(amounts), width="stretch")

    sec("100 € su ciascun titolo")
    normalized = c["prices"] / c["prices"].iloc[0] * 100
    st.line_chart(normalized, color=PALETTE[: len(normalized.columns)], height=300)

# ================================================================ VISUAL
elif view == "Visual":
    c = computed
    col_ai, col_radar = st.columns([1.3, 1], gap="large")
    with col_ai:
        sec("Analisi automatica")
        insights = generate_insights(
            period, c["cum_return"], c["contributions"], c["avg_corr"],
            c["drawdown"], c["beta"], BENCHMARK,
        )
        for insight in insights:
            st.markdown(insight)
        st.caption("Generata con regole deterministiche sui tuoi dati, non da un modello.")
    with col_radar:
        sec("Radar di rischio")
        st.altair_chart(radar_chart(c["radar"]), width="stretch")

    col_galaxy, col_timeline = st.columns([1.15, 1], gap="large")
    with col_galaxy:
        sec("La tua galassia")
        st.caption("Dimensione = peso · colore = rendimento · vicinanza = correlazione")
        if len(amounts) >= 2:
            corr = correlation_matrix(c["returns"], min_periods=c["min_periods"])
            weights_s = pd.Series({p["ticker"]: p["weight"] for p in portfolio})
            st.altair_chart(
                galaxy_chart(corr, weights_s, per_ticker_cumulative_return(c["prices"])),
                width="stretch",
            )
        else:
            st.info("Servono almeno 2 titoli.")
    with col_timeline:
        sec("Mese per mese")
        monthly = monthly_returns(c["pf_daily"])
        if len(monthly) >= 2:
            st.altair_chart(monthly_bars(monthly), width="stretch")
            best, worst = monthly.idxmax(), monthly.idxmin()
            st.caption(
                f"Mese migliore: **{best.strftime('%b %Y')}** ({monthly.max():+.1%}) "
                f"· peggiore: **{worst.strftime('%b %Y')}** ({monthly.min():+.1%})"
            )
        else:
            st.info("Periodo troppo corto per la vista mensile.")

    if len(amounts) >= 2:
        col_wr, col_wr_txt = st.columns([1.5, 1], gap="large")
        with col_wr:
            sec("Peso investito vs contributo al rischio")
            weights_series_ui = pd.Series({p["ticker"]: p["weight"] for p in portfolio})
            st.altair_chart(
                weight_vs_risk_bars(weights_series_ui, c["contributions"]),
                width="stretch",
            )
        with col_wr_txt:
            sec("Come leggerlo")
            top_c = c["contributions"].index[0]
            gap = float(c["contributions"].iloc[0] - weights_series_ui.get(top_c, 0))
            st.markdown(
                f"Quando la barra ambra supera quella blu, il titolo pesa sul "
                f"rischio **più di quanto pesi sul capitale**. "
                f"Oggi **{top_c}** genera il "
                f"**{c['contributions'].iloc[0]:.0%}** del rischio "
                f"({gap:+.0%} rispetto al suo peso)."
            )
            st.caption(
                "Contributo marginale alla varianza di portafoglio: tiene conto "
                "di volatilità e correlazioni, non solo dell'importo investito."
            )

    sec('Simulatore "What if?"')
    col_sim_in, col_sim_out = st.columns([1, 2], gap="large")
    with col_sim_in:
        sim_ticker = st.selectbox("Se questo titolo...", sorted(amounts))
        shock_pct = st.slider("...si muovesse di", -50, 50, -20, step=5, format="%d%%")
    with col_sim_out:
        impact = simulate_shock(c["returns"], portfolio, sim_ticker, shock_pct / 100)
        s1, s2, s3 = st.columns(3)
        s1.metric("Portafoglio oggi", eur(total))
        s2.metric(
            "Dopo lo shock (con contagio)",
            eur(total * (1 + impact["total"])),
            delta=f"{impact['total']:+.1%}",
        )
        s3.metric(
            "Solo effetto diretto",
            eur(total * (1 + impact["direct"])),
            delta=f"{impact['direct']:+.1%}", delta_color="off",
        )
        st.caption(
            "Il contagio stima come gli altri titoli reagirebbero, "
            "usando i loro beta storici verso il titolo colpito."
        )

# ================================================================ OTTIMIZZA
elif view == "Ottimizza":
    c = computed
    if len(amounts) < 2:
        st.info("Servono almeno 2 titoli per l'ottimizzazione.")
    else:
        sec("Frontiera efficiente di Markowitz")
        st.caption(
            "Per ogni livello di rischio, il miglior rendimento raggiungibile "
            "combinando i tuoi titoli (rendimenti attesi = medie aritmetiche "
            "storiche, convenzione di Markowitz)."
        )
        returns = c["returns"]
        candidates = {
            "Attuale": pd.Series({p["ticker"]: p["weight"] for p in portfolio}),
            "Minimo rischio": minimum_variance_weights(returns),
            "Massimo Sharpe": max_sharpe_weights(returns, risk_free_rate=risk_free),
        }

        def pf_stats(weights: pd.Series) -> tuple[float, float]:
            pf = [{"ticker": t, "weight": float(w)} for t, w in weights.items() if w > 0]
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
                width="stretch",
            )
        with col_compare:
            st.markdown("**Confronto**")
            compare = points.set_index("nome")
            compare["sharpe"] = (
                (compare["annual_return"] - risk_free) / compare["annual_volatility"]
            )
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
                    col: st.column_config.NumberColumn(col, format="percent")
                    for col in candidates
                },
            )

# ================================================================ CORRELAZIONI
elif view == "Correlazioni":
    sec("Quali titoli si muovono insieme")
    st.caption(
        "Correlazione dei rendimenti giornalieri: **+1** = identici, "
        "**0** = indipendenti, **-1** = opposti."
    )
    all_prices = market_db_required("corr")
    if all_prices is None:
        st.info("Serve il database Nasdaq-100: esegui `python download_nasdaq100.py`.")
    else:
        col_sel, col_per = st.columns([2, 1])
        with col_sel:
            corr_ticker = st.selectbox(
                "Titolo di riferimento", sorted(all_prices.columns), index=None,
                placeholder="Scegli un titolo del Nasdaq-100...",
            )
        with col_per:
            corr_period = st.selectbox("Periodo", list(PERIOD_DAYS), index=2,
                                       key="corr_period")
        if corr_ticker:
            cutoff = all_prices.index[-1] - pd.Timedelta(days=PERIOD_DAYS[corr_period])
            window_returns = compute_daily_returns(all_prices.loc[all_prices.index >= cutoff])
            mp = max(15, min(60, len(window_returns) // 2))
            corr = correlations_with(window_returns, corr_ticker, min_periods=mp)

            col_top, col_bottom = st.columns(2, gap="large")
            with col_top:
                st.markdown(f"**Si muovono INSIEME a {corr_ticker}**")
                st.altair_chart(correlation_bars(corr.head(10)), width="stretch")
            with col_bottom:
                st.markdown(f"**INDIPENDENTI o OPPOSTI a {corr_ticker}**")
                st.altair_chart(
                    correlation_bars(corr.tail(10).sort_values()), width="stretch"
                )

    if computed is not None and len(amounts) >= 2:
        sec("Diversificazione del tuo portafoglio")
        pf_corr = correlation_matrix(computed["returns"],
                                     min_periods=computed["min_periods"])
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
                    f"Coppia più legata: **{tightest[0]} – {tightest[1]}** "
                    f"({pairs.max():+.2f})"
                )
        with col_heat:
            st.altair_chart(correlation_heatmap(pf_corr), width="stretch")

# ================================================================ FONDAMENTALI
elif view == "Fondamentali":
    sec("Ricavi, margini, debito, crescita e multipli")
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
                    "sector": st.column_config.TextColumn("Settore"),
                    "dividend_yield": st.column_config.NumberColumn(
                        "Div. yield", format="%.2f%%"
                    ),
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
                    "net_margin": st.column_config.NumberColumn(
                        "Margine netto", format="percent"
                    ),
                    "total_debt": st.column_config.NumberColumn("Debito", format="compact"),
                    "debt_to_equity": st.column_config.NumberColumn(
                        "Debito/Equity", format="%.1f"
                    ),
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

            sec("Scheda titolo")
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
                    dna_card_html(scores, f"{row['name']}", title="STOCK DNA"),
                    unsafe_allow_html=True,
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

# ================================================================ MERCATO
elif view == "Mercato":
    sec("I 103 componenti del Nasdaq-100 a confronto")
    all_prices = market_db_required("mercato")
    if all_prices is None:
        st.info("Database non ancora scaricato: esegui `python download_nasdaq100.py`.")
    else:
        ndx_period = st.selectbox("Periodo di confronto", list(PERIOD_DAYS), index=2)
        cutoff = all_prices.index[-1] - pd.Timedelta(days=PERIOD_DAYS[ndx_period])
        window = all_prices.loc[all_prices.index >= cutoff]

        stats = pd.DataFrame(
            {
                "period_return": per_ticker_cumulative_return(window),
                "annual_volatility": compute_daily_returns(window).std()
                * TRADING_DAYS**0.5,
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
            "Rendimento cumulato nel periodo (prezzi in USD). "
            "Aggiorna i dati con `python download_nasdaq100.py`."
        )

        sec("PI Score — ranking multifattore")
        st.caption(
            "Punteggio composito 0-100: **50% momentum 12-1 mesi** (Jegadeesh & "
            "Titman 1993), **30% bassa volatilità** (Baker et al. 2011), "
            "**20% trend** (distanza dalla media a 200 giorni). Regolarità "
            "storiche documentate in letteratura, non garanzie — e non un "
            "consiglio di investimento."
        )
        pi_window = compute_daily_returns(all_prices).tail(TRADING_DAYS)
        pi_ranking = composite_scores(pi_window).dropna().head(15)
        st.dataframe(
            pi_ranking.rename_axis("ticker").reset_index(),
            column_config={
                "ticker": st.column_config.TextColumn("Ticker"),
                "momentum": st.column_config.ProgressColumn(
                    "Momentum", min_value=0, max_value=100, format="%.0f"
                ),
                "low_vol": st.column_config.ProgressColumn(
                    "Bassa volatilità", min_value=0, max_value=100, format="%.0f"
                ),
                "trend": st.column_config.ProgressColumn(
                    "Trend", min_value=0, max_value=100, format="%.0f"
                ),
                "pi_score": st.column_config.NumberColumn("PI Score", format="%.0f"),
            },
            hide_index=True,
            width="stretch",
        )

# ================================================================ BACKTEST
elif view == "Backtest":
    sec("E se avessi seguito una strategia?")
    st.caption(
        "Ribilanciamento trimestrale, pesi calcolati solo sui dati precedenti "
        "(nessuno sguardo al futuro). Limiti: niente costi di transazione, prezzi "
        "in USD, universo = componenti ATTUALI del Nasdaq-100 (survivorship bias)."
    )
    all_prices = market_db_required("backtest")
    if all_prices is None:
        st.info("Serve il database Nasdaq-100: esegui `python download_nasdaq100.py`.")
    else:
        options = [
            "Equipesato Nasdaq-100",
            "Momentum (top 10 a 6 mesi)",
            "PI Multifactor (top 10)",
        ]
        if len(amounts) >= 2:
            options += [
                "Il tuo portafoglio (buy & hold)",
                "Massimo Sharpe sui tuoi titoli",
                "Minima varianza sui tuoi titoli",
            ]
        chosen = st.multiselect("Strategie da confrontare", options, default=options[:3])
        col_bt1, col_bt2 = st.columns(2)
        with col_bt1:
            bt_years = st.select_slider(
                "Orizzonte", ["1 anno", "2 anni", "5 anni"], "5 anni"
            )
        with col_bt2:
            cost_bps = st.slider(
                "Costi di transazione (bps per ribilanciamento)", 0, 50, 20, step=5,
                help="20 bps = 0.20% sul controvalore scambiato: realistico per un "
                "retail su titoli liquidi. Il buy & hold paga solo l'acquisto iniziale.",
            )
        cutoff = all_prices.index[-1] - pd.Timedelta(days=PERIOD_DAYS[bt_years])
        window = all_prices.loc[all_prices.index >= cutoff]

        if chosen:
            with st.spinner("Eseguo i backtest..."):
                curves = {}
                try:
                    if "Equipesato Nasdaq-100" in chosen:
                        curves["Equipesato Nasdaq-100"] = run_backtest(
                            window, equal_weight, cost_bps=cost_bps
                        )
                    if "Momentum (top 10 a 6 mesi)" in chosen:
                        curves["Momentum (top 10 a 6 mesi)"] = run_backtest(
                            window, lambda w: momentum_top(w, top_n=10),
                            cost_bps=cost_bps,
                        )
                    if "PI Multifactor (top 10)" in chosen:
                        curves["PI Multifactor (top 10)"] = run_backtest(
                            window,
                            lambda w: multifactor_weights(w, top_n=10),
                            lookback=273,  # serve ~1 anno per il momentum 12-1
                            cost_bps=cost_bps,
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
                                my_prices, max_sharpe, cost_bps=cost_bps
                            )
                        if "Minima varianza sui tuoi titoli" in chosen:
                            curves["Minima varianza sui tuoi titoli"] = run_backtest(
                                my_prices, min_variance, cost_bps=cost_bps
                            )
                except ValueError as exc:
                    st.error(f"{exc}")

            if curves:
                equity = pd.DataFrame(curves).dropna(how="all")
                cols = st.columns(len(curves))
                for col, (name, curve) in zip(cols, curves.items()):
                    col.metric(name, f"{curve.iloc[-1] / 100 - 1:+.0%}")
                st.line_chart(equity, color=PALETTE[: len(curves)], height=380)

                strategy_stats = pd.DataFrame(
                    [
                        {
                            "Strategia": name,
                            "Rendimento": curve.iloc[-1] / 100 - 1,
                            "Volatilità annua": curve.pct_change().std() * TRADING_DAYS**0.5,
                            "Max drawdown": float((curve / curve.cummax() - 1).min()),
                        }
                        for name, curve in curves.items()
                    ]
                )
                st.dataframe(
                    strategy_stats,
                    column_config={
                        "Rendimento": st.column_config.NumberColumn(format="percent"),
                        "Volatilità annua": st.column_config.NumberColumn(format="percent"),
                        "Max drawdown": st.column_config.NumberColumn(format="percent"),
                    },
                    hide_index=True,
                    width="stretch",
                )
                st.caption(
                    f"Curve a base 100, costi {cost_bps} bps per ribilanciamento. "
                    "Il rendimento non è tutto: guarda volatilità e drawdown."
                )
