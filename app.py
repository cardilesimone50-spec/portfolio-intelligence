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
from src.analytics.interpret import (
    interpret_beta,
    interpret_correlation,
    interpret_drawdown,
    interpret_sharpe,
    interpret_sortino,
    interpret_volatility,
)
from src.ui.components import (
    breakdown_html,
    empty_state,
    kpi_row_html,
    dna_card_html,
    eur,
    hero_html,
    render_landing,
    sec,
)
from src.analytics.insights import (
    dna_label,
    executive_summary,
    health_breakdown,
    usd_exposure,
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
# soglie di volatilità annua per profilo di rischio (dichiarate nella UI)
PROFILE_VOL = {"Prudente": 0.10, "Moderato": 0.18, "Aggressivo": 0.30}

st.set_page_config(
    page_title="Portfolio Intelligence", page_icon="◆", layout="wide",
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
    .st-key-navbar [data-testid="stSegmentedControl"] button,
    .st-key-navbar [role="radiogroup"] button {{
        background: transparent !important;
        border: none !important;
        border-radius: 0 !important;
        border-bottom: 2px solid transparent !important;
        padding: 6px 14px 10px !important;
    }}
    .st-key-navbar button p {{
        font-size: 0.78rem !important; font-weight: 600;
        letter-spacing: 0.07em; text-transform: uppercase;
        color: var(--muted) !important;
    }}
    .st-key-navbar button[aria-checked="true"],
    .st-key-navbar button[kind="segmented_controlActive"] {{
        border-bottom-color: var(--accent) !important;
    }}
    .st-key-navbar button[aria-checked="true"] p,
    .st-key-navbar button[kind="segmented_controlActive"] p {{
        color: #ffffff !important;
    }}
    .st-key-navbar {{
        border-bottom: 1px solid var(--line);
        position: sticky; top: 0; z-index: 99;
        background: rgba(11, 14, 19, 0.82);
        backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);
    }}

    /* ---- profondità e hover ---- */
    .panel, .hero-panel {{
        box-shadow: 0 8px 26px rgba(0, 0, 0, 0.28);
        transition: transform 0.18s ease, border-color 0.18s ease;
    }}
    .panel:hover, .hero-panel:hover {{
        transform: translateY(-2px);
        border-color: rgba(247, 166, 0, 0.28);
    }}
    .pos-row {{ transition: background 0.15s ease; border-radius: 8px; }}
    .pos-row:hover {{ background: rgba(255, 255, 255, 0.03); }}
    .stButton button, .stDownloadButton button {{
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }}
    .stButton button:hover, .stDownloadButton button:hover {{
        transform: translateY(-1px);
        box-shadow: 0 6px 16px rgba(0, 0, 0, 0.3);
    }}

    /* ---- KPI card con icona ---- */
    .kpi-row {{ display: flex; gap: 16px; flex-wrap: wrap; margin: 4px 0 6px; }}
    .kpi {{
        flex: 1; min-width: 210px;
        background: var(--panel); border: 1px solid var(--line);
        border-radius: 14px; padding: 18px 20px;
        box-shadow: 0 8px 22px rgba(0, 0, 0, 0.25);
        transition: transform 0.18s ease, border-color 0.18s ease;
        animation: fadeUpSubtle 0.3s ease-out both;
    }}
    .kpi:hover {{ transform: translateY(-2px); border-color: rgba(247,166,0,0.3); }}
    .kpi-top {{ display: flex; justify-content: space-between; align-items: center; }}
    .kpi-icon {{
        width: 34px; height: 34px; border-radius: 9px; flex-shrink: 0;
        display: flex; align-items: center; justify-content: center;
    }}
    .kpi-label {{
        font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.1em;
        color: var(--muted); font-weight: 600; padding-right: 8px;
    }}
    .kpi-value {{
        font-size: 1.7rem; font-weight: 700; margin-top: 8px;
        font-variant-numeric: tabular-nums; letter-spacing: -0.02em;
    }}
    .kpi-sub {{ font-size: 0.75rem; color: var(--muted); margin-top: 4px;
                line-height: 1.45; }}
    @keyframes fadeUpSubtle {{
        from {{ opacity: 0; transform: translateY(6px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}

    /* ---- empty state ---- */
    .empty {{
        text-align: center; padding: 54px 30px;
        border: 1.5px dashed rgba(255, 255, 255, 0.14);
        border-radius: 16px; margin: 20px 0;
    }}
    .empty-icon {{
        width: 46px; height: 46px; margin: 0 auto 14px; border-radius: 12px;
        display: flex; align-items: center; justify-content: center;
        background: rgba(247, 166, 0, 0.1); color: var(--accent);
    }}
    .empty-title {{ font-weight: 700; font-size: 1.05rem; }}
    .empty-hint {{
        color: var(--muted); font-size: 0.9rem; margin-top: 6px;
        max-width: 430px; margin-left: auto; margin-right: auto; line-height: 1.5;
    }}

    /* ---- spinner brandizzato ---- */
    [data-testid="stSpinner"] i {{
        border-top-color: var(--accent) !important;
        border-right-color: rgba(247, 166, 0, 0.25) !important;
    }}

    /* ---- responsive ---- */
    @media (max-width: 920px) {{
        .hero-panel {{ flex-direction: column; text-align: center; gap: 16px; }}
        .kpi {{ min-width: 100%; }}
        .landing-hero {{ padding: 44px 26px 40px !important; }}
        .landing-title {{ font-size: 2.1rem !important; }}
        .glass-row {{ flex-direction: column; }}
    }}

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

    /* ---- card posizioni (sidebar) ---- */
    .pos-row {{
        display: flex; align-items: center; gap: 11px;
        padding: 9px 2px;
        border-bottom: 1px solid rgba(255,255,255,0.05);
    }}
    .avatar {{
        width: 34px; height: 34px; border-radius: 10px; flex-shrink: 0;
        display: flex; align-items: center; justify-content: center;
        font-size: 0.7rem; font-weight: 800; color: #0b0e13;
        letter-spacing: 0.02em;
    }}
    .pos-main {{ flex: 1; min-width: 0; }}
    .pos-ticker {{ font-weight: 700; font-size: 0.9rem; line-height: 1.2; }}
    .pos-name {{
        font-size: 0.7rem; color: var(--muted); max-width: 160px;
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }}
    .pos-amt {{
        font-size: 0.78rem; color: var(--muted);
        font-variant-numeric: tabular-nums;
    }}
    .pos-weight-track {{
        margin-top: 4px; height: 3px; border-radius: 2px;
        background: rgba(255,255,255,0.08);
    }}
    .pos-weight-fill {{ height: 100%; border-radius: 2px; }}
    .pos-pct {{
        font-size: 0.82rem; font-weight: 700; color: #c5cad6;
        font-variant-numeric: tabular-nums;
    }}

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
    [data-testid="stMainMenu"] {{ display: none; }}
    [data-testid="stPopover"] > button {{
        border: none !important; background: transparent !important;
        color: var(--muted) !important; font-weight: 700;
    }}
    [data-testid="stPopover"] > button:hover {{ color: #e6e8ee !important; }}
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
        empty_state(
            "Database prezzi non ancora presente",
            "Servono 5 anni di prezzi giornalieri per i 103 titoli del "
            "Nasdaq-100: si scaricano una sola volta, poi si aggiornano "
            "in modo incrementale.",
            icon="folder",
        )
        if st.button("Scarica i dati (~1 minuto)", key=f"dl_{view_key}", type="primary"):
            from download_nasdaq100 import update_nasdaq100

            with st.spinner("Scarico 5 anni di prezzi da Yahoo Finance..."):
                update_nasdaq100()
            st.rerun()
    return prices


# ================================================================ SIDEBAR
if "holdings" not in st.session_state:
    st.session_state.holdings = {"AAPL": 4000.0, "MSFT": 3000.0, "NVDA": 3000.0}

_db_for_search = load_market_db()
KNOWN_TICKERS = sorted(_db_for_search.columns) if _db_for_search is not None else [
    "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "AVGO", "COST", "NFLX",
]

with st.sidebar:
    st.markdown(
        '<div class="brand" style="font-size:.9rem">◆ PORTFOLIO <b>INTELLIGENCE</b></div>',
        unsafe_allow_html=True,
    )
    sec("Il tuo portafoglio")

    with st.form("add_position", clear_on_submit=True, border=False):
        new_ticker = st.selectbox(
            "Titolo",
            KNOWN_TICKERS,
            index=None,
            placeholder="Cerca un titolo (es. AAPL)...",
            accept_new_options=True,
            label_visibility="collapsed",
        )
        new_amount = st.number_input(
            "Importo (€)", min_value=100.0, value=1000.0, step=500.0,
            label_visibility="collapsed",
        )
        if st.form_submit_button("Aggiungi", width="stretch", type="primary"):
            if new_ticker:
                key = str(new_ticker).upper().strip()
                st.session_state.holdings[key] = (
                    st.session_state.holdings.get(key, 0.0) + float(new_amount)
                )
                st.rerun()

    holdings = st.session_state.holdings
    total = sum(holdings.values())
    if holdings:
        max_amount = max(holdings.values())
        sorted_tickers = sorted(holdings, key=holdings.get, reverse=True)
        known_names = st.session_state.get("names", {})
        for i, ticker in enumerate(sorted_tickers):
            amount = holdings[ticker]
            color = PALETTE[sorted(holdings).index(ticker) % len(PALETTE)]
            weight = amount / total if total else 0
            company = known_names.get(ticker, "")
            name_html = f'<div class="pos-name">{company}</div>' if company else ""
            col_card, col_menu = st.columns([5, 1], gap="small")
            with col_card:
                st.markdown(
                    f"""<div class="pos-row">
                      <div class="avatar" style="background:{color}">{ticker[:4]}</div>
                      <div class="pos-main">
                        <div class="pos-ticker">{ticker}
                          <span class="pos-amt">· {eur(amount)}</span></div>
                        {name_html}
                        <div class="pos-weight-track"><div class="pos-weight-fill"
                          style="width:{weight:.0%};background:{color}"></div></div>
                      </div>
                      <div class="pos-pct">{weight:.0%}</div>
                    </div>""",
                    unsafe_allow_html=True,
                )
            with col_menu:
                with st.popover("···"):
                    updated = st.number_input(
                        "Importo (€)", min_value=0.0, value=float(amount),
                        step=500.0, key=f"edit_{ticker}",
                    )
                    col_ok, col_del = st.columns(2)
                    if col_ok.button("Salva", key=f"save_{ticker}", width="stretch"):
                        if updated > 0:
                            st.session_state.holdings[ticker] = float(updated)
                        else:
                            st.session_state.holdings.pop(ticker, None)
                        st.rerun()
                    if col_del.button("Rimuovi", key=f"del_{ticker}", width="stretch"):
                        st.session_state.holdings.pop(ticker, None)
                        st.rerun()
        st.caption(f"Totale: **{eur(total)}** · {len(holdings)} titoli")
    else:
        empty_state(
            "Portafoglio vuoto",
            "Cerca un titolo qui sopra e aggiungilo con il suo importo.",
            icon="folder",
        )

    with st.expander("Importa da CSV / Excel"):
        uploaded = st.file_uploader(
            "Posizione titoli in CSV o Excel", type=["csv", "xlsx", "xls"],
            help="Esporta dal tuo broker la POSIZIONE TITOLI (detta anche "
            "dossier o patrimonio), non l'estratto dei movimenti di conto. "
            "Formati supportati: CSV ed Excel — i PDF non sono leggibili. "
            "Colonne attese: titolo/ticker e importo/controvalore, oppure "
            "quantità e prezzo.",
        )
        if uploaded is not None:
            file_id = f"{uploaded.name}-{uploaded.size}"
            if st.session_state.get("last_upload") != file_id:
                try:
                    st.session_state.holdings = parse_positions(
                        uploaded.getvalue(), uploaded.name
                    )
                    st.session_state.last_upload = file_id
                    st.toast(f"Importate {len(st.session_state.holdings)} posizioni")
                    st.rerun()
                except ValueError as exc:
                    st.error(f"Import fallito: {exc}")

    saved = list_portfolios()
    with st.expander("Portafogli salvati"):
        portfolio_name = st.text_input("Nome", value="Il mio portafoglio")
        if st.button("Salva composizione attuale", width="stretch") and holdings:
            save_portfolio(portfolio_name, holdings)
            st.toast(f"Portafoglio «{portfolio_name}» salvato")
        if saved:
            selected_saved = st.selectbox("Carica", sorted(saved), index=None,
                                          placeholder="Scegli un portafoglio...")
            if selected_saved and st.button("Carica nel portafoglio", width="stretch"):
                st.session_state.holdings = dict(saved[selected_saved])
                st.rerun()

    with st.expander("Impostazioni"):
        period = st.selectbox(
            "Orizzonte storico", ["1mo", "6mo", "1y", "2y", "5y"], index=2, key="pf_period"
        )
        in_eur = st.toggle(
            "Misura tutto in euro",
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
        risk_profile = st.selectbox(
            "Profilo di rischio",
            ["Non impostato", "Prudente", "Moderato", "Aggressivo"],
            index=0,
            help="Soglie di volatilità annua attesa dichiarate: prudente fino al "
            "10%, moderato fino al 18%, aggressivo fino al 30%. Il check-up "
            "confronta il portafoglio con la soglia del profilo.",
        )

amounts = dict(st.session_state.holdings)
total = sum(amounts.values())

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
        usd_weight = usd_exposure(portfolio)
        breakdown = health_breakdown(dna, radar, usd_weight)
        health = portfolio_health_score(breakdown)

        computed = {
            "returns": returns, "prices": prices, "pf_daily": pf_daily,
            "pf_value": pf_value, "bench_daily": bench_daily,
            "annual_ret": annual_ret, "annual_vol": annual_vol,
            "drawdown": drawdown, "avg_corr": avg_corr, "var_95": var_95,
            "beta": beta, "alpha": alpha, "min_periods": min_periods,
            "cum_return": cum_return, "risk_score": risk_score,
            "contributions": contributions, "radar": radar, "fund": fund,
            "dna": dna, "health": health, "breakdown": breakdown,
            "usd_weight": usd_weight,
        }
        if "name" in fund.columns:
            st.session_state["names"] = {
                **st.session_state.get("names", {}),
                **fund["name"].dropna().to_dict(),
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
def _start_checkup() -> None:
    st.session_state.nav = "Check-up"


with st.container(key="navbar"):
    view = st.segmented_control(
        "Sezione",
        ["Home", "Check-up", "Analisi", "Visual", "Ottimizza", "Correlazioni",
         "Fondamentali", "Mercato", "Backtest", "Clienti"],
        default="Home",
        label_visibility="collapsed",
        key="nav",
    )
view = view or "Home"

if compute_error:
    st.error(compute_error)

NEEDS_PORTFOLIO = {"Check-up", "Analisi", "Visual", "Ottimizza"}

# ================================================================ HOME
if view == "Home":
    render_landing(on_start=_start_checkup)

elif view in NEEDS_PORTFOLIO and computed is None:
    if not compute_error:
        empty_state(
            "Nessun portafoglio da analizzare",
            "Aggiungi un titolo con il suo importo nella barra laterale, "
            "carica un CSV del broker o un portafoglio salvato.",
        )

# ================================================================ CHECK-UP
elif view == "Check-up":
    c = computed
    col_hero, col_equity = st.columns([1, 1.4], gap="large")
    with col_hero:
        st.markdown(
            hero_html(c["health"], eur(total * (1 + c["cum_return"])),
                      c["cum_return"], period,
                      today_move=float(c["pf_daily"].iloc[-1])),
            unsafe_allow_html=True,
        )
        st.caption(
            "Health Score: media di sei componenti — diversificazione, "
            "concentrazione, volatilità, esposizione valutaria, drawdown, "
            "qualità dei bilanci."
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

    col_break, col_exec = st.columns([1, 1.4], gap="large")
    with col_break:
        st.markdown(breakdown_html(c["breakdown"]), unsafe_allow_html=True)
    with col_exec:
        sec("Executive summary")
        st.markdown(
            executive_summary(
                period, c["cum_return"], c["breakdown"], c["contributions"],
                c["avg_corr"], c["usd_weight"], c["drawdown"], c["beta"], BENCHMARK,
            )
        )
        st.caption(
            "Sintesi generata da regole deterministiche sulle metriche calcolate: "
            "nessun testo inventato."
        )

    sec("Le tue posizioni")
    cum_by_ticker = per_ticker_cumulative_return(c["prices"])
    normalized_pos = c["prices"] / c["prices"].apply(lambda s: s.dropna().iloc[0])
    last_session = c["returns"].iloc[-1]
    fund_names = c["fund"]["name"] if "name" in c["fund"].columns else pd.Series(dtype=str)
    position_rows = [
        {
            "Titolo": t,
            "Nome": fund_names.get(t, ""),
            "Importo": amounts[t],
            "Peso": amounts[t] / total,
            "Oggi": float(last_session[t]) if t in last_session.index else None,
            "Rendimento": cum_by_ticker.get(t),
            "Andamento": normalized_pos[t].dropna().tolist()[-130:],
        }
        for t in sorted(amounts, key=amounts.get, reverse=True)
    ]
    st.dataframe(
        pd.DataFrame(position_rows),
        column_config={
            "Titolo": st.column_config.TextColumn("Titolo"),
            "Nome": st.column_config.TextColumn("Società"),
            "Importo": st.column_config.NumberColumn("Importo", format="%.0f €"),
            "Peso": st.column_config.NumberColumn("Peso", format="percent"),
            "Oggi": st.column_config.NumberColumn("Ultima seduta", format="percent"),
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
    if risk_profile in PROFILE_VOL and c["annual_vol"] > PROFILE_VOL[risk_profile]:
        band = PROFILE_VOL[risk_profile]
        problems.insert(
            0,
            f"Per un profilo **{risk_profile.lower()}** (volatilità attesa fino al "
            f"{band:.0%}), il portafoglio oscilla il "
            f"**{c['annual_vol'] / band - 1:.0%} in più** della soglia.",
        )
    top_problems = (session_alerts + problems)[:5]
    if top_problems:
        for problem in top_problems:
            st.markdown(problem)
    else:
        st.success("Nessun problema rilevato dalle regole monitorate.")

    sec("Il tuo rischio, in euro")
    st.markdown(
        kpi_row_html(
            [
                {
                    "icon": "wave",
                    "label": "Oscillazione tipica in 1 anno",
                    "value": f"± {eur(total * c['annual_vol'])}",
                    "sub": f"{c['annual_vol']:.1%} annuo · "
                    + interpret_volatility(
                        c["annual_vol"],
                        (
                            compute_daily_returns(_db_for_search).std()
                            * TRADING_DAYS**0.5
                            if _db_for_search is not None
                            else None
                        ),
                    ),
                },
                {
                    "icon": "bolt",
                    "label": "In una giornata nera (VaR 95%)",
                    "value": eur(total * c["var_95"]),
                    "sub": "nel 95% dei giorni non perdi più di questa cifra "
                    "(stima storica)",
                    "color": LOSS,
                },
                {
                    "icon": "down",
                    "label": "Nella peggior discesa del periodo",
                    "value": eur(total * c["drawdown"]),
                    "sub": f"{c['drawdown']:.1%} dal picco (max drawdown) "
                    "investendo questa cifra",
                    "color": LOSS,
                },
            ]
        ),
        unsafe_allow_html=True,
    )
    st.caption("Stime dall'andamento storico del periodo: non sono una previsione.")

    sec("Cosa puoi fare (simulato sui tuoi dati)")

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
        st.markdown(simulation)
    if not simulations and candidates_sim:
        st.markdown(
            "Abbiamo simulato le mosse più ovvie sui tuoi dati, ma **nessuna "
            "migliora il profilo attuale** — un buon segno per come sei pesato:"
        )
        for text in discarded:
            st.caption("Scartata: " + text)
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
            "Scarica il report PDF",
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
                names=st.session_state.get("names", {}),
            ),
            file_name=f"portfolio_report_{pd.Timestamp.now():%Y%m%d}.pdf",
            mime="application/pdf",
            width="stretch",
            type="primary",
        )
    with col_log:
        if st.button("Salva nello storico", width="stretch"):
            log_analysis(
                portfolio_name, period, total, c["cum_return"],
                c["risk_score"], health=c["health"],
            )
            st.toast("Analisi salvata")
    with col_hist:
        history = load_analyses()
        if not history.empty:
            with st.expander(f"Storico analisi ({len(history)})"):
                trend = history.dropna(subset=["health"])
                trend = trend[trend["portfolio"] == portfolio_name]
                if len(trend) >= 2:
                    series = pd.Series(
                        trend["health"].to_numpy(dtype=float),
                        index=pd.to_datetime(trend["timestamp"]),
                    ).sort_index()
                    st.altair_chart(
                        simple_line(series, y_format=".0f"), width="stretch"
                    )
                    delta_h = int(series.iloc[-1] - series.iloc[0])
                    st.caption(
                        f"Health Score di «{portfolio_name}» nel tempo: "
                        f"{delta_h:+d} punti dalla prima analisi salvata."
                    )
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
                        "health": st.column_config.NumberColumn("Health /100"),
                    },
                    hide_index=True,
                )

# ================================================================ ANALISI
elif view == "Analisi":
    c = computed
    sharpe = annualized_sharpe(c["returns"], portfolio, risk_free_rate=risk_free)
    sortino = sortino_ratio(c["returns"], portfolio, risk_free_rate=risk_free)

    # percentile di volatilità contro i singoli titoli del Nasdaq-100 (se in DB)
    _db = load_market_db()
    universe_vols = (
        compute_daily_returns(_db).std() * TRADING_DAYS**0.5 if _db is not None else None
    )

    sec("Rendimento")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Investimento", eur(total))
    m2.metric(
        "Rendimento annualizzato (composto)",
        eur(total * c["annual_ret"]),
        delta=f"{c['annual_ret']:+.1%}",
        help="CAGR del periodo osservato: non sovrastima in presenza di volatilità.",
    )
    m3.metric("Sharpe ratio", f"{sharpe:.2f}",
              help=f"Calcolato con risk-free {risk_free:.1%}.")
    m3.caption(interpret_sharpe(sharpe))
    m4.metric("Sortino ratio", f"{sortino:.2f}")
    m4.caption(interpret_sortino(sortino, sharpe))

    sec("Rischio")
    r1, r2, r3, r4 = st.columns(4)
    r1.metric(
        "Oscillazione tipica in 1 anno",
        f"± {eur(total * c['annual_vol'])}",
        delta=f"{c['annual_vol']:.1%}", delta_color="off",
    )
    r1.caption(interpret_volatility(c["annual_vol"], universe_vols))
    r2.metric("Perdita massima storica", f"{c['drawdown']:.1%}")
    r2.caption(interpret_drawdown(c["drawdown"]))
    r3.metric("VaR 95% (1 giorno)", eur(total * c["var_95"]))
    r3.caption(
        "Nel 95% delle giornate storiche non hai perso più di questa cifra."
    )
    r4.metric(
        f"Beta vs {BENCHMARK}", f"{c['beta']:.2f}",
        delta=f"α {c['alpha']:+.1%}/anno", delta_color="off",
    )
    r4.caption(interpret_beta(c["beta"], BENCHMARK))
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
                st.warning(interpret_correlation(avg_corr))
            elif avg_corr > 0.3:
                st.info(interpret_correlation(avg_corr))
            else:
                st.success(interpret_correlation(avg_corr))
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

# ================================================================ CLIENTI
elif view == "Clienti":
    sec("Vista consulente — tutti i portafogli salvati")
    st.caption(
        "Ogni portafoglio salvato è un cliente: semaforo, valore, Health Score "
        "e il problema più urgente, in un colpo d'occhio. Per aprirne uno: "
        "barra laterale → Portafogli salvati → Carica."
    )

    @st.cache_data(ttl=900, show_spinner=False)
    def quick_client_analysis(
        items: tuple, period_key: str, eur_flag: bool
    ) -> dict:
        amounts_c = dict(items)
        total_c = sum(amounts_c.values())
        pf_c = [
            {"ticker": t, "weight": a / total_c} for t, a in amounts_c.items()
        ]
        prices_c = cached_prices(tuple(sorted(amounts_c)), period_key)
        if eur_flag:
            prices_c = convert_to_eur(prices_c, cached_eurusd(period_key))
        returns_c = compute_daily_returns(prices_c)
        daily_c = portfolio_daily_returns(returns_c, pf_c)
        value_c = (1 + daily_c).cumprod()
        vol_c = portfolio_volatility(returns_c, pf_c) * TRADING_DAYS**0.5
        dd_c = max_drawdown(value_c)
        mp_c = max(15, min(60, len(returns_c) // 2))
        corr_c = average_pairwise_correlation(returns_c, min_periods=mp_c)
        radar_c = radar_scores(vol_c, pf_c, dd_c, corr_c)
        fund_c = cached_fundamentals(tuple(sorted(amounts_c)))
        dna_c = dna_scores(fund_c, pf_c, vol_c, corr_c)
        breakdown_c = health_breakdown(dna_c, radar_c, usd_exposure(pf_c))
        contributions_c = risk_contributions(returns_c, pf_c)
        problems_c = find_problems(pf_c, fund_c, contributions_c, corr_c, radar_c)
        return {
            "health": portfolio_health_score(breakdown_c),
            "value": total_c * float(value_c.iloc[-1]),
            "invested": total_c,
            "cum": float(value_c.iloc[-1] - 1),
            "vol": vol_c,
            "problem": problems_c[0].replace("**", "") if problems_c else
            "Nessun problema rilevato dalle regole monitorate.",
        }

    book = list_portfolios()
    if not book:
        empty_state(
            "Nessun cliente nel libro",
            "Salva almeno un portafoglio (barra laterale → Portafogli salvati) "
            "per vederlo comparire qui con semaforo e problema principale.",
            icon="folder",
        )
    else:
        rows_html = ""
        failures = []
        with st.spinner("Analizzo il libro clienti..."):
            for client_name in sorted(book):
                try:
                    a = quick_client_analysis(
                        tuple(sorted(book[client_name].items())), period, in_eur
                    )
                except ValueError as exc:
                    failures.append(f"{client_name}: {exc}")
                    continue
                color = (
                    GAIN if a["health"] >= 67
                    else AMBER if a["health"] >= 34 else LOSS
                )
                chg_css = "up" if a["cum"] >= 0 else "down"
                rows_html += f"""
                <div class="kpi" style="display:flex;align-items:center;
                     gap:16px;margin-bottom:10px;min-width:100%">
                  <div style="width:10px;height:10px;border-radius:50%;
                       background:{color};flex-shrink:0"></div>
                  <div style="min-width:150px">
                    <div style="font-weight:700">{client_name}</div>
                    <div class="kpi-sub">{eur(a["invested"])} investiti ·
                         vol. {a["vol"]:.0%}</div>
                  </div>
                  <div style="min-width:120px">
                    <div class="kpi-sub">VALORE</div>
                    <div style="font-weight:700;font-variant-numeric:tabular-nums">
                         {eur(a["value"])}
                         <span class="chg {chg_css}" style="font-size:.8rem">
                         {a["cum"]:+.1%}</span></div>
                  </div>
                  <div style="flex:1" class="kpi-sub">{a["problem"]}</div>
                  <div style="font-family:var(--font-display);font-size:1.5rem;
                       font-weight:700;color:{color}">{a["health"]}
                       <span style="font-size:.7rem;color:var(--muted)">/100</span>
                  </div>
                </div>"""
        st.markdown(rows_html, unsafe_allow_html=True)
        for failure in failures:
            st.warning(f"Analisi non riuscita — {failure}")
        st.caption(
            f"{len(book)} clienti · orizzonte {period} · "
            + ("valori in EUR, cambio incluso" if in_eur else "valute originali")
            + " · analisi aggiornate ogni 15 minuti."
        )
