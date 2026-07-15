"""SmarteeFinance — Portfolio Intelligence: the honest 60-second portfolio check-up.

Avvio: streamlit run app.py
"""

import os
import random
import time

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
    executive_summary,
    find_opportunities,
    find_problems,
    generate_insights,
    generate_suggestions,
    health_breakdown,
    monthly_returns,
    portfolio_health_score,
    portfolio_risk_score,
    radar_scores,
    reduce_position,
    risk_contributions,
    stock_scores,
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
    beta_alpha,
    expected_shortfall,
    max_drawdown,
    sharpe_from_daily,
    sortino_from_daily,
    sortino_ratio,
    value_at_risk,
)
from src.analytics.simulation import simulate_shock
from src.data import yahoo_client
from src.data.cache import load_nasdaq100_prices
from src.data.fx import convert_to_eur, fetch_eurusd
from src.data.importers import parse_positions
from src.data.rates import fetch_risk_free_rate
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
from src.ui.components import (
    breakdown_html,
    compliance_footer,
    dna_card_html,
    empty_state,
    eur,
    hero_html,
    kpi_row_html,
    position_card_html,
    render_landing,
    sec,
    ticker_preview_html,
)
from src.ui.identity import DEV_ADVISOR, auth_configured, current_advisor, is_authenticated
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

# ponte secrets→ambiente: i secrets di Streamlit non diventano env var da soli.
# Impostando DATABASE_URL nei secrets, lo store passa da SQLite a Postgres.
try:
    if "DATABASE_URL" in st.secrets:
        os.environ.setdefault("DATABASE_URL", str(st.secrets["DATABASE_URL"]))
except Exception:  # noqa: BLE001 — nessun secrets.toml in locale: si resta su SQLite
    pass

BENCHMARK = "QQQ"  # ETF sul Nasdaq-100
TRADING_DAYS = 252
PERIOD_DAYS = {"1 mese": 30, "6 mesi": 182, "1 anno": 365, "2 anni": 730, "5 anni": 1826}
AMBER = "#d97706"  # status mid-band only (gauge/health)
ACCENT = "#1E40AF"  # brand primary (Stripe/Mercury blue)
# annual volatility thresholds per risk profile (declared in the UI)
PROFILE_VOL = {"Conservative": 0.10, "Moderate": 0.18, "Aggressive": 0.30}

st.set_page_config(
    page_title="SmarteeFinance · Portfolio Intelligence",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------- design system
st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Space+Grotesk:wght@500;600;700&display=swap');

    :root {{
        --panel: #ffffff;
        --panel-2: #ffffff;
        --line: #E2E8F0;
        --muted: #64748b;
        --ink: #0F172A;
        --accent: {ACCENT};
        --accent-soft: rgba(30, 64, 175, 0.08);
        --accent-border: rgba(30, 64, 175, 0.28);
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
        font-size: 1.02rem; letter-spacing: 0.14em; color: var(--ink);
        text-transform: uppercase; font-weight: 500;
    }}
    .brand b {{ color: var(--accent); font-weight: 700; }}
    .brand-product {{
        font-family: var(--font-ui) !important; text-transform: none;
        font-size: 0.7rem; font-weight: 600; color: var(--muted);
        letter-spacing: 0.01em; margin-left: 10px; padding-left: 10px;
        border-left: 1px solid var(--line);
    }}
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
        color: var(--ink) !important;
    }}
    .st-key-navbar {{
        border-bottom: 1px solid var(--line);
        position: sticky; top: 0; z-index: 99;
        background: rgba(247, 248, 250, 0.85);
        backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);
    }}
    /* sub-nav contestuale: chip discrete sotto la nav primaria */
    .st-key-subnav {{ margin: 4px 0 2px; }}
    .st-key-subnav [data-testid="stSegmentedControl"] button {{
        background: transparent !important; border: 1px solid var(--line) !important;
        border-radius: 8px !important; padding: 3px 14px !important;
        margin-right: 6px;
    }}
    .st-key-subnav button p {{
        font-size: 0.72rem !important; font-weight: 600; letter-spacing: 0.04em;
        text-transform: none; color: var(--muted) !important;
    }}
    .st-key-subnav button[aria-checked="true"],
    .st-key-subnav button[kind="segmented_controlActive"] {{
        background: var(--accent-soft) !important;
        border-color: var(--accent-border) !important;
    }}
    .st-key-subnav button[aria-checked="true"] p,
    .st-key-subnav button[kind="segmented_controlActive"] p {{
        color: var(--accent) !important;
    }}

    /* ---- profondità e hover ---- */
    .panel, .hero-panel {{
        box-shadow: 0 1px 2px rgba(15,23,42,0.04), 0 4px 12px rgba(15,23,42,0.04);
        transition: transform 0.18s ease, border-color 0.18s ease;
    }}
    .panel:hover, .hero-panel:hover {{
        transform: translateY(-2px);
        border-color: rgba(30,64,175,0.28);
    }}
    .pos-row {{ transition: background 0.15s ease; border-radius: 8px; }}
    .pos-row:hover {{ background: rgba(20, 25, 35, 0.03); }}
    .stButton button, .stDownloadButton button {{
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }}
    .stButton button:hover, .stDownloadButton button:hover {{
        transform: translateY(-1px);
        box-shadow: 0 4px 14px rgba(30,64,175,0.14);
    }}

    /* ---- KPI card con icona ---- */
    .kpi-row {{ display: flex; gap: 16px; flex-wrap: wrap; margin: 4px 0 6px; }}
    .kpi {{
        flex: 1; min-width: 210px;
        background: var(--panel); border: 1px solid var(--line);
        border-radius: 18px; padding: 20px 22px;
        box-shadow: 0 1px 2px rgba(15,23,42,0.04), 0 4px 12px rgba(15,23,42,0.04);
        transition: transform 0.18s ease, border-color 0.18s ease;
        animation: fadeUpSubtle 0.3s ease-out both;
    }}
    .kpi:hover {{ transform: translateY(-2px); border-color: rgba(30,64,175,0.3); }}
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
        border: 1.5px dashed rgba(20, 25, 35, 0.14);
        border-radius: 18px; margin: 20px 0;
    }}
    .empty-icon {{
        width: 46px; height: 46px; margin: 0 auto 14px; border-radius: 12px;
        display: flex; align-items: center; justify-content: center;
        background: rgba(30,64,175,0.1); color: var(--accent);
    }}
    .compliance {{
        margin: 42px auto 8px; max-width: 900px; text-align: center;
        font-size: 0.72rem; line-height: 1.5; color: #6b7280;
        border-top: 1px solid var(--line); padding-top: 16px;
    }}
    .empty-title {{ font-weight: 700; font-size: 1.05rem; }}
    .empty-hint {{
        color: var(--muted); font-size: 0.9rem; margin-top: 6px;
        max-width: 430px; margin-left: auto; margin-right: auto; line-height: 1.5;
    }}

    /* ---- spinner brandizzato ---- */
    [data-testid="stSpinner"] i {{
        border-top-color: var(--accent) !important;
        border-right-color: rgba(30,64,175,0.25) !important;
    }}

    .brand-product {{ white-space: nowrap; }}

    /* ---- responsive ---- */
    @media (max-width: 920px) {{
        .hero-panel {{ flex-direction: column; text-align: center; gap: 16px; }}
        .kpi {{ min-width: 100%; }}
        .landing-hero {{ padding: 44px 26px 40px !important; }}
        .landing-title {{ font-size: 2.1rem !important; }}
        .glass-row {{ flex-direction: column; }}
    }}
    @media (max-width: 640px) {{
        .block-container {{ padding-left: 0.6rem; padding-right: 0.6rem; }}
        .topbar {{ flex-direction: column; align-items: flex-start; gap: 2px; }}
        .brand {{ font-size: 0.92rem; letter-spacing: 0.08em; }}
        .brand-product {{
            display: block; margin: 3px 0 0; padding: 0; border-left: none;
        }}
        .brand-tag {{ font-size: 0.66rem; }}
        /* nav: horizontal scroll instead of wrapping onto 2 rows */
        .st-key-navbar [role="radiogroup"] {{
            flex-wrap: nowrap !important; overflow-x: auto; width: 100%;
            -webkit-overflow-scrolling: touch; scrollbar-width: none;
        }}
        .st-key-navbar [role="radiogroup"]::-webkit-scrollbar {{ display: none; }}
        .st-key-navbar button {{
            flex: 0 0 auto !important; padding: 6px 12px 10px !important;
        }}
        .st-key-navbar button p {{
            font-size: 0.72rem !important; letter-spacing: 0.04em;
            white-space: nowrap !important; overflow: visible !important;
            text-overflow: clip !important;
        }}
        .hero-panel {{ padding: 20px 18px; }}
        .hero-meta .big {{ font-size: 2.1rem; }}
        .gauge {{ width: 112px; height: 112px; }}
        .gauge-inner {{ width: 90px; height: 90px; }}
        .kpi-value {{ font-size: 1.5rem; }}
        [data-testid="stMetricValue"] {{ font-size: 1.4rem !important; }}
        .sec {{ margin: 20px 0 8px; }}
    }}

    /* ---- metriche flat: niente scatole, solo numeri e separatori ---- */
    .panel {{
        background: var(--panel); border: 1px solid var(--line);
        border-radius: 18px; padding: 22px 26px; height: 100%;
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
                                   rgba(20,25,35,0.08) 0);
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
    .dna-name {{ width: 72px; font-size: 0.86rem; color: #3a4150; }}
    .dna-track {{
        flex: 1; background: rgba(20,25,35,0.08); border-radius: 4px; height: 6px;
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
        border-bottom: 1px solid rgba(20,25,35,0.06);
    }}
    .avatar {{
        width: 34px; height: 34px; border-radius: 10px; flex-shrink: 0;
        display: flex; align-items: center; justify-content: center;
        font-size: 0.7rem; font-weight: 800; color: #ffffff;
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
        background: rgba(20,25,35,0.08);
    }}
    .pos-weight-fill {{ height: 100%; border-radius: 2px; }}
    .pos-pct {{
        font-size: 0.82rem; font-weight: 700; color: #3a4150;
        font-variant-numeric: tabular-nums;
    }}

    /* ---- anteprima titolo (aggiungi) ---- */
    .ticker-preview {{
        display: flex; align-items: center; gap: 12px;
        background: var(--accent-soft);
        border: 1px solid var(--accent-border);
        border-radius: 14px; padding: 12px 14px; margin: 4px 0 10px;
        animation: fadeUpSubtle 0.25s ease-out both;
    }}
    .tp-main {{ flex: 1; min-width: 0; }}
    .tp-name {{
        font-weight: 700; font-size: 0.92rem; line-height: 1.2;
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }}
    .tp-meta {{
        font-size: 0.7rem; color: var(--muted); text-transform: uppercase;
        letter-spacing: 0.04em; margin-top: 1px;
    }}
    .tp-price {{
        font-size: 0.9rem; font-weight: 700; margin-top: 4px;
        font-variant-numeric: tabular-nums;
    }}
    .tp-chg {{ font-size: 0.8rem; font-weight: 600; margin-left: 6px; }}
    .tp-chg.up {{ color: var(--gain); }}
    .tp-chg.down {{ color: var(--loss); }}

    /* ---- sidebar ---- */
    [data-testid="stSidebar"] {{
        background: var(--panel-2); border-right: 1px solid var(--line);
    }}
    [data-testid="stSidebar"] .sec {{ margin: 10px 0 6px; }}
    [data-testid="stSidebar"] hr {{ margin: 12px 0; }}

    /* ---- bottoni ed expander ---- */
    .stButton button, .stDownloadButton button {{
        border-radius: 8px; border: 1px solid rgba(20,25,35,0.12);
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
    [data-testid="stPopover"] > button:hover {{ color: var(--ink) !important; }}
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


@st.cache_data(ttl=3600, show_spinner=False)
def cached_risk_free() -> float:
    """Baseline risk-free (T-bill 3M USA, ^IRX) come frazione annua, con fallback."""
    return fetch_risk_free_rate()


@st.cache_data(ttl=1800, show_spinner=False)
def ticker_preview(ticker: str) -> dict | None:
    """Nome, prezzo e variazione di seduta di un titolo, per l'anteprima.

    Robusto: se la sorgente non risponde restituisce None senza rompere la UI.
    """
    from src.data.yahoo_client import get_ticker_info

    try:
        info = get_ticker_info(ticker)
    except Exception:
        return None
    if not info or not info.get("shortName"):
        return None
    return {
        "name": info.get("shortName") or info.get("longName") or "",
        "sector": info.get("sector") or "",
        "price": info.get("currentPrice") or info.get("regularMarketPrice"),
        "currency": info.get("currency") or "USD",
        "change": info.get("regularMarketChangePercent"),
    }


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
            "5 years of daily prices for the 103 Nasdaq-100 stocks are "
            "needed: downloaded once, then refreshed incrementally.",
            icon="folder",
        )
        if st.button("Download data (~1 minute)", key=f"dl_{view_key}", type="primary"):
            from download_nasdaq100 import update_nasdaq100

            with st.spinner("Downloading 5 years of prices from Yahoo Finance..."):
                update_nasdaq100()
            st.rerun()
    return prices


# ================================================================ SIDEBAR
SAMPLE_PORTFOLIO = {"AAPL": 4000.0, "MSFT": 3000.0, "NVDA": 3000.0}
if "holdings" not in st.session_state:
    st.session_state.holdings = {}

_db_for_search = load_market_db()
KNOWN_TICKERS = (
    sorted(_db_for_search.columns)
    if _db_for_search is not None
    else [
        "AAPL",
        "MSFT",
        "NVDA",
        "GOOGL",
        "AMZN",
        "META",
        "TSLA",
        "AVGO",
        "COST",
        "NFLX",
    ]
)

# ================================================================ ONBOARDING GATE
# Three-stage flow before the platform unlocks:
#   landing  -> only the hero + "Analyze my portfolio" is reachable
#   input    -> you are forced onto the page that collects the tickers
#   loading  -> a spinning gear + an investing quote, then the platform opens
if "stage" not in st.session_state:
    st.session_state.stage = "landing"

QUOTES = [
    ("Risk comes from not knowing what you're doing.", "Warren Buffett"),
    ("Be fearful when others are greedy, and greedy when others are fearful.", "Warren Buffett"),
    (
        "The stock market is a device for transferring money "
        "from the impatient to the patient.",
        "Warren Buffett",
    ),
    ("Know what you own, and know why you own it.", "Peter Lynch"),
    ("The big money is not in the buying and selling, but in the waiting.", "Charlie Munger"),
    (
        "The investor's chief problem — and even his worst enemy — "
        "is likely to be himself.",
        "Benjamin Graham",
    ),
    ("The four most dangerous words in investing are: 'this time it's different.'", "John Templeton"),
    ("In investing, what is comfortable is rarely profitable.", "Robert Arnott"),
]

GATE_CSS = """
<style>
/* while gated, nothing but the screen itself is reachable */
[data-testid="stSidebar"],
[data-testid="stSidebarCollapsedControl"],
[data-testid="collapsedControl"] { display: none !important; }

.gate-head { max-width: 620px; margin: 8px auto 4px; text-align: center; }
.gate-title {
    font-family: var(--font-display); font-weight: 700;
    font-size: 2rem; letter-spacing: -0.01em; color: var(--ink); margin: 0;
}
.gate-sub { color: var(--muted); font-size: 0.98rem; margin-top: 10px; line-height: 1.5; }
.gate-step {
    display: inline-block; font-size: 0.7rem; font-weight: 600; letter-spacing: 0.14em;
    text-transform: uppercase; color: var(--accent);
    background: var(--accent-soft); border: 1px solid var(--accent-border);
    border-radius: 999px; padding: 4px 14px; margin-bottom: 14px;
}

/* loading screen: full-screen overlay so no stale widgets show through */
.loading-wrap {
    position: fixed; inset: 0; z-index: 99999;
    background: #F8FAFC; padding: 24px; text-align: center;
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    gap: 26px;
}
.gear { width: 96px; height: 96px; animation: gearspin 3.4s linear infinite; }
.gear svg { width: 100%; height: 100%; display: block; }
@keyframes gearspin { to { transform: rotate(360deg); } }
.loading-quote {
    font-family: var(--font-display); font-weight: 600;
    font-size: 1.35rem; line-height: 1.45; color: var(--ink);
    max-width: 560px;
}
.loading-author {
    font-size: 0.9rem; font-weight: 600; letter-spacing: 0.06em;
    text-transform: uppercase; color: var(--accent);
}
.loading-hint { color: var(--muted); font-size: 0.85rem; }
</style>
"""

GEAR_SVG = (
    '<div class="gear"><svg viewBox="0 0 24 24" fill="none" '
    'xmlns="http://www.w3.org/2000/svg">'
    '<path d="M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7Z" '
    'stroke="var(--accent)" stroke-width="1.4"/>'
    '<path d="M19.4 13a7.6 7.6 0 0 0 .05-2l1.7-1.32a.5.5 0 0 0 .12-.64l-1.6-2.77a.5.5 0 0 0'
    '-.6-.22l-2 .8a7.4 7.4 0 0 0-1.73-1l-.3-2.12a.5.5 0 0 0-.5-.42h-3.2a.5.5 0 0 0-.5.42'
    'l-.3 2.12a7.4 7.4 0 0 0-1.73 1l-2-.8a.5.5 0 0 0-.6.22l-1.6 2.77a.5.5 0 0 0 .12.64L4.55 11'
    'a7.6 7.6 0 0 0 0 2l-1.7 1.32a.5.5 0 0 0-.12.64l1.6 2.77a.5.5 0 0 0 .6.22l2-.8a7.4 7.4 0 0 0'
    ' 1.73 1l.3 2.12a.5.5 0 0 0 .5.42h3.2a.5.5 0 0 0 .5-.42l.3-2.12a7.4 7.4 0 0 0 1.73-1l2 .8'
    'a.5.5 0 0 0 .6-.22l1.6-2.77a.5.5 0 0 0-.12-.64L19.4 13Z" '
    'stroke="var(--accent)" stroke-width="1.4" stroke-linejoin="round"/>'
    "</svg></div>"
)


def _go_input() -> None:
    st.session_state.stage = "input"


def _go_loading() -> None:
    st.session_state.stage = "loading"


def _load_sample() -> None:
    st.session_state.holdings = dict(SAMPLE_PORTFOLIO)


def _gate_add() -> None:
    chosen = st.session_state.get("gate_ticker")
    if not chosen:
        return
    k = str(chosen).upper().strip()
    amt = float(st.session_state.get("gate_amount") or 0)
    if amt <= 0:
        return
    st.session_state.holdings[k] = st.session_state.holdings.get(k, 0.0) + amt
    st.session_state.gate_ticker = None


if st.session_state.stage != "app":
    st.markdown(GATE_CSS, unsafe_allow_html=True)

    # ---- stage 1: landing ------------------------------------------------
    if st.session_state.stage == "landing":
        render_landing(on_start=_go_input)

    # ---- stage 2: you must enter the tickers -----------------------------
    elif st.session_state.stage == "input":
        st.markdown(
            """
            <div class="gate-head">
              <div class="gate-step">Step 1 of 2 · Build your portfolio</div>
              <div class="gate-title">Which stocks do you hold?</div>
              <div class="gate-sub">Add each position with the amount you have invested.
              Nothing else is available until you tell us what to analyze.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        _l, mid, _r = st.columns([1, 2, 1])
        with mid:
            new_ticker = st.selectbox(
                "Search stock",
                KNOWN_TICKERS,
                index=None,
                placeholder="Search by symbol (e.g. AAPL)...",
                accept_new_options=True,
                label_visibility="collapsed",
                key="gate_ticker",
            )
            if new_ticker:
                key = str(new_ticker).upper().strip()
                color = PALETTE[abs(hash(key)) % len(PALETTE)]
                st.markdown(
                    ticker_preview_html(key, color, ticker_preview(key)),
                    unsafe_allow_html=True,
                )
                col_amt, col_add = st.columns([3, 2], gap="small")
                with col_amt:
                    st.number_input(
                        "Amount",
                        min_value=100.0,
                        value=1000.0,
                        step=500.0,
                        label_visibility="collapsed",
                        key="gate_amount",
                    )
                with col_add:
                    st.button(
                        "＋ Add", width="stretch", type="primary", on_click=_gate_add
                    )

            gate_holdings = st.session_state.holdings
            if gate_holdings:
                sec("Your holdings")
                gate_total = sum(gate_holdings.values())
                for ticker in sorted(gate_holdings, key=gate_holdings.get, reverse=True):
                    amount = gate_holdings[ticker]
                    color = PALETTE[sorted(gate_holdings).index(ticker) % len(PALETTE)]
                    weight = amount / gate_total if gate_total else 0
                    company = st.session_state.get("names", {}).get(ticker, "")
                    col_card, col_del = st.columns([6, 1], gap="small")
                    with col_card:
                        st.markdown(
                            position_card_html(ticker, amount, weight, color, company),
                            unsafe_allow_html=True,
                        )
                    with col_del:
                        if st.button("✕", key=f"gate_del_{ticker}", width="stretch"):
                            st.session_state.holdings.pop(ticker, None)
                            st.rerun()
                st.caption(f"Total: **{eur(gate_total)}** · {len(gate_holdings)} stocks")
            else:
                st.caption("Search a stock above and add it with its amount.")
                st.button(
                    "Try a sample portfolio (AAPL · MSFT · NVDA)",
                    on_click=_load_sample,
                    width="stretch",
                )

            st.divider()
            st.button(
                "Analyze my portfolio →",
                type="primary",
                width="stretch",
                on_click=_go_loading,
                disabled=not st.session_state.holdings,
            )

    # ---- stage 3: gear + investing quote, then the platform opens --------
    elif st.session_state.stage == "loading":
        quote, author = random.choice(QUOTES)
        st.markdown(
            '<div class="loading-wrap">'
            + GEAR_SVG
            + f'<div class="loading-quote">“{quote}”</div>'
            + f'<div class="loading-author">— {author}</div>'
            + '<div class="loading-hint">Crunching the numbers on your portfolio…</div>'
            + "</div>",
            unsafe_allow_html=True,
        )
        time.sleep(2.8)
        st.session_state.stage = "app"
        st.rerun()

    st.stop()

# consulente corrente (tenant): portafogli e analisi sono isolati per advisor
advisor = current_advisor()

with st.sidebar:
    st.markdown(
        '<div class="brand" style="font-size:.9rem">◆ SMARTEE<b>FINANCE</b></div>',
        unsafe_allow_html=True,
    )

    # identità consulente + login/logout (B2B multi-tenant)
    if auth_configured():
        if is_authenticated():
            st.caption(f"Advisor: **{advisor}**")
            if st.button("Log out", width="stretch"):
                st.logout()
        else:
            st.caption("Sign in to load your client book.")
            if st.button("Log in", type="primary", width="stretch"):
                st.login()
    else:
        st.caption(f"Advisor: **{advisor}** · demo mode")

    sec("Add a stock")

    def _add_holding() -> None:
        # runs as a callback (before widgets re-instantiate), so clearing the
        # add_ticker widget key here is allowed by Streamlit
        chosen = st.session_state.get("add_ticker")
        if not chosen:
            return
        k = str(chosen).upper().strip()
        amt = float(st.session_state.get("add_amount") or 0)
        if amt <= 0:
            return
        st.session_state.holdings[k] = st.session_state.holdings.get(k, 0.0) + amt
        st.session_state.add_ticker = None

    new_ticker = st.selectbox(
        "Search stock",
        KNOWN_TICKERS,
        index=None,
        placeholder="Search by symbol (e.g. AAPL)...",
        accept_new_options=True,
        label_visibility="collapsed",
        key="add_ticker",
    )

    if new_ticker:
        key = str(new_ticker).upper().strip()
        color = PALETTE[abs(hash(key)) % len(PALETTE)]
        st.markdown(
            ticker_preview_html(key, color, ticker_preview(key)),
            unsafe_allow_html=True,
        )

        col_amt, col_add = st.columns([3, 2], gap="small")
        with col_amt:
            st.number_input(
                "Amount",
                min_value=100.0,
                value=1000.0,
                step=500.0,
                label_visibility="collapsed",
                key="add_amount",
            )
        with col_add:
            st.button("＋ Add", width="stretch", type="primary", on_click=_add_holding)
    else:
        st.caption("Search a stock to see its name and price, then add it.")

    sec("Your holdings")

    holdings = st.session_state.holdings
    total = sum(holdings.values())
    if holdings:
        sorted_tickers = sorted(holdings, key=holdings.get, reverse=True)
        known_names = st.session_state.get("names", {})
        for ticker in sorted_tickers:
            amount = holdings[ticker]
            color = PALETTE[sorted(holdings).index(ticker) % len(PALETTE)]
            weight = amount / total if total else 0
            company = known_names.get(ticker, "")
            col_card, col_menu = st.columns([5, 1], gap="small")
            with col_card:
                st.markdown(
                    position_card_html(ticker, amount, weight, color, company),
                    unsafe_allow_html=True,
                )
            with col_menu, st.popover("···"):
                updated = st.number_input(
                    "Amount (€)",
                    min_value=0.0,
                    value=float(amount),
                    step=500.0,
                    key=f"edit_{ticker}",
                )
                col_ok, col_del = st.columns(2)
                if col_ok.button("Save", key=f"save_{ticker}", width="stretch"):
                    if updated > 0:
                        st.session_state.holdings[ticker] = float(updated)
                    else:
                        st.session_state.holdings.pop(ticker, None)
                    st.rerun()
                if col_del.button("Remove", key=f"del_{ticker}", width="stretch"):
                    st.session_state.holdings.pop(ticker, None)
                    st.rerun()
        st.caption(f"Total: **{eur(total)}** · {len(holdings)} stocks")
    else:
        empty_state(
            "Empty portfolio",
            "Search a stock above and add it with its amount.",
            icon="folder",
        )

    with st.expander("Import from CSV / Excel"):
        uploaded = st.file_uploader(
            "Securities position in CSV or Excel",
            type=["csv", "xlsx", "xls"],
            help="Export your broker's SECURITIES POSITION (also called holdings "
            "or portfolio), not the account transactions statement. "
            "Supported formats: CSV and Excel — PDFs are not readable. "
            "Expected columns: ticker/symbol and amount/value, or "
            "quantity and price.",
        )
        if uploaded is not None:
            file_id = f"{uploaded.name}-{uploaded.size}"
            if st.session_state.get("last_upload") != file_id:
                try:
                    st.session_state.holdings = parse_positions(uploaded.getvalue(), uploaded.name)
                    st.session_state.last_upload = file_id
                    st.toast(f"Imported {len(st.session_state.holdings)} positions")
                    st.rerun()
                except ValueError as exc:
                    st.error(f"Import failed: {exc}")

    saved = list_portfolios(advisor)
    with st.expander("Saved portfolios"):
        portfolio_name = st.text_input("Name", value="My portfolio")
        if st.button("Save current composition", width="stretch") and holdings:
            save_portfolio(advisor, portfolio_name, holdings)
            st.toast(f'Portfolio "{portfolio_name}" saved')
        if saved:
            selected_saved = st.selectbox(
                "Load", sorted(saved), index=None, placeholder="Choose a portfolio..."
            )
            if selected_saved and st.button("Load into portfolio", width="stretch"):
                st.session_state.holdings = dict(saved[selected_saved])
                st.rerun()

    with st.expander("Settings"):
        period = st.selectbox(
            "Historical horizon", ["1mo", "6mo", "1y", "2y", "5y"], index=2, key="pf_period"
        )
        in_eur = st.toggle(
            "Measure everything in euros",
            value=True,
            help="US stocks trade in dollars: converting to EUR makes the metrics "
            "include EUR/USD swings too — the real risk for a European "
            "investor.",
        )
        rf_baseline_pct = min(10.0, max(0.0, round(cached_risk_free() * 100, 2)))
        risk_free = (
            st.number_input(
                "Annual risk-free rate (%)",
                min_value=0.0,
                max_value=10.0,
                value=rf_baseline_pct,
                step=0.25,
                help="Baseline = current US 3-month T-bill (^IRX), fetched live and "
                "editable. Used in Sharpe, Sortino and optimization. Using 0 would "
                "overstate these ratios.",
            )
            / 100
        )
        st.caption(f"Baseline ^IRX (3M T-bill): {rf_baseline_pct:.2f}%")
        risk_profile = st.selectbox(
            "Risk profile",
            ["Not set", "Conservative", "Moderate", "Aggressive"],
            index=0,
            help="Declared expected annual volatility thresholds: conservative up to "
            "10%, moderate up to 18%, aggressive up to 30%. The check-up "
            "compares the portfolio with the profile threshold.",
        )

amounts = dict(st.session_state.holdings)
total = sum(amounts.values())

portfolio = (
    [{"ticker": t, "weight": amount / total} for t, amount in amounts.items()] if total else []
)

# ================================================================ SHARED COMPUTATIONS
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
            "returns": returns,
            "prices": prices,
            "pf_daily": pf_daily,
            "pf_value": pf_value,
            "bench_daily": bench_daily,
            "annual_ret": annual_ret,
            "annual_vol": annual_vol,
            "drawdown": drawdown,
            "avg_corr": avg_corr,
            "var_95": var_95,
            "beta": beta,
            "alpha": alpha,
            "min_periods": min_periods,
            "cum_return": cum_return,
            "risk_score": risk_score,
            "contributions": contributions,
            "radar": radar,
            "fund": fund,
            "dna": dna,
            "health": health,
            "breakdown": breakdown,
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
    <span class="brand">◆ SMARTEE<b>FINANCE</b><span class="brand-product">Portfolio Intelligence</span></span>
    <span class="brand-tag">{"EUR · currency included" if in_eur else "original currencies"}
    · price source: {yahoo_client.last_price_source}</span></div>""",
    unsafe_allow_html=True,
)


# nav a due livelli: 5 voci macro + sub-nav contestuale che rimappa alla vista
# (Home non è più qui: è il gate di onboarding che precede la piattaforma)
MACRO_ORDER = ["Check-up", "Analysis", "Strategies", "Market", "Clients"]
SUBNAV = {
    "Analysis": [("Metrics", "Analisi"), ("Charts", "Visual")],
    "Strategies": [("Optimization", "Ottimizza"), ("Backtest", "Backtest")],
    "Market": [
        ("Nasdaq-100", "Mercato"),
        ("Correlations", "Correlazioni"),
        ("Fundamentals", "Fondamentali"),
    ],
}

with st.container(key="navbar"):
    macro = st.segmented_control(
        "Section", MACRO_ORDER, default="Check-up", label_visibility="collapsed", key="nav"
    )
macro = macro or "Check-up"

if macro in SUBNAV:
    labels = [label for label, _ in SUBNAV[macro]]
    with st.container(key="subnav"):
        sub = st.segmented_control(
            "Subsection",
            labels,
            default=labels[0],
            label_visibility="collapsed",
            key=f"sub_{macro}",
        )
    view = dict(SUBNAV[macro]).get(sub or labels[0], SUBNAV[macro][0][1])
else:
    view = macro

if compute_error:
    st.error(compute_error)

NEEDS_PORTFOLIO = {"Check-up", "Analisi", "Visual", "Ottimizza"}

# ================================================================ EMPTY PORTFOLIO
if view in NEEDS_PORTFOLIO and computed is None:
    if not compute_error:
        empty_state(
            "No portfolio to analyze",
            "Add a stock with its amount in the sidebar, "
            "import a broker CSV or load a saved portfolio.",
        )

# ================================================================ CHECK-UP
elif view == "Check-up":
    c = computed
    col_hero, col_equity = st.columns([1, 1.4], gap="large")
    with col_hero:
        st.markdown(
            hero_html(
                c["health"],
                eur(total * (1 + c["cum_return"])),
                c["cum_return"],
                period,
                today_move=float(c["pf_daily"].iloc[-1]),
            ),
            unsafe_allow_html=True,
        )
        st.caption(
            "Health Score: the average of six components — diversification, "
            "concentration, volatility, currency exposure, drawdown, "
            "balance-sheet quality."
        )
        if c["dna"]:
            st.markdown(f"**{dna_label(c['dna'])}**")
    with col_equity:
        sec(f"Capital over time ({period})")
        st.altair_chart(
            equity_area(total * (1 + c["pf_daily"]).cumprod(), total),
            width="stretch",
        )
        st.caption("Dashed line = capital invested today, projected backwards.")

    col_break, col_exec = st.columns([1, 1.4], gap="large")
    with col_break:
        st.markdown(breakdown_html(c["breakdown"]), unsafe_allow_html=True)
    with col_exec:
        sec("Executive summary")
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
        st.caption(
            "Summary generated by deterministic rules on the computed metrics: no invented text."
        )

    sec("Your holdings")
    cum_by_ticker = per_ticker_cumulative_return(c["prices"])
    normalized_pos = c["prices"] / c["prices"].apply(lambda s: s.dropna().iloc[0])
    last_session = c["returns"].iloc[-1]
    fund_names = c["fund"]["name"] if "name" in c["fund"].columns else pd.Series(dtype=str)
    position_rows = [
        {
            "Ticker": t,
            "Company": fund_names.get(t, ""),
            "Amount": amounts[t],
            "Weight": amounts[t] / total,
            "Today": float(last_session[t]) if t in last_session.index else None,
            "Return": cum_by_ticker.get(t),
            "Trend": normalized_pos[t].dropna().tolist()[-130:],
        }
        for t in sorted(amounts, key=amounts.get, reverse=True)
    ]
    st.dataframe(
        pd.DataFrame(position_rows),
        column_config={
            "Ticker": st.column_config.TextColumn("Ticker"),
            "Company": st.column_config.TextColumn("Company"),
            "Amount": st.column_config.NumberColumn("Amount", format="%.0f €"),
            "Weight": st.column_config.NumberColumn("Weight", format="percent"),
            "Today": st.column_config.NumberColumn("Last session", format="percent"),
            "Return": st.column_config.NumberColumn(f"Return ({period})", format="percent"),
            "Trend": st.column_config.AreaChartColumn(f"Trend ({period})", width="medium"),
        },
        hide_index=True,
        width="stretch",
    )

    sec("Top problems")
    problems = find_problems(portfolio, c["fund"], c["contributions"], c["avg_corr"], c["radar"])
    session_alerts = [
        a
        for a in evaluate_alerts(
            c["returns"], portfolio, c["contributions"], c["avg_corr"], c["drawdown"]
        )
        if "Last session" in a
    ]
    if risk_profile in PROFILE_VOL and c["annual_vol"] > PROFILE_VOL[risk_profile]:
        band = PROFILE_VOL[risk_profile]
        problems.insert(
            0,
            f"For a **{risk_profile.lower()}** profile (expected volatility up to "
            f"{band:.0%}), the portfolio swings "
            f"**{c['annual_vol'] / band - 1:.0%} more** than the threshold.",
        )
    top_problems = (session_alerts + problems)[:5]
    if top_problems:
        for problem in top_problems:
            st.markdown(problem)
    else:
        st.success("No problems flagged by the monitored rules.")

    sec("Your risk, in euros")
    st.markdown(
        kpi_row_html(
            [
                {
                    "icon": "wave",
                    "label": "Typical 1-year swing",
                    "value": f"± {eur(total * c['annual_vol'])}",
                    "sub": f"{c['annual_vol']:.1%} per year · "
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
                    "label": "On a bad day (95% VaR)",
                    "value": eur(total * c["var_95"]),
                    "sub": "on 95% of days you don't lose more than this (historical estimate)",
                    "color": LOSS,
                },
                {
                    "icon": "down",
                    "label": "In the worst drop of the period",
                    "value": eur(total * c["drawdown"]),
                    "sub": f"{c['drawdown']:.1%} from the peak (max drawdown) investing this amount",
                    "color": LOSS,
                },
            ]
        ),
        unsafe_allow_html=True,
    )
    st.caption("Estimates from the period's historical performance: not a forecast.")

    sec("Scenarios on your data")

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
        candidates_sim[f"Halve {top_t} (redistributing to the others)"] = reduce_position(
            portfolio, top_t, 0.5
        )
    if len(portfolio) >= 3 and c["radar"].get("Concentration", 0) > 25:
        candidates_sim["Equal-weight all holdings"] = equal_weight_portfolio(portfolio)

    simulations, discarded = [], []
    for name, new_pf in candidates_sim.items():
        new_vol, new_health = simulate_change(new_pf)
        improves = new_health > c["health"] or (
            new_health == c["health"] and new_vol < c["annual_vol"] * 0.98
        )
        text = (
            f"**{name}**: annual swing from ± {eur(total * c['annual_vol'])} "
            f"to ± {eur(total * new_vol)}, Health Score from {c['health']} "
            f"to **{new_health}**."
        )
        (simulations if improves else discarded).append(text)

    for simulation in simulations:
        st.markdown(simulation)
    if not simulations and candidates_sim:
        st.markdown(
            "We simulated the most obvious moves on your data, but **none "
            "improves the current profile** — a good sign for how you're weighted:"
        )
        for text in discarded:
            st.caption("Discarded: " + text)
    for opportunity in find_opportunities(portfolio, c["fund"])[:2]:
        st.markdown(opportunity)
    if not candidates_sim:
        st.caption("No scenario proposed: the weights are already well distributed.")

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
                f"Return ({period})",
                f"{c['cum_return']:+.1%}",
                f"{bench_cum:+.1%}",
                "Total change over the observation window, dividends not reinvested.",
            ),
            (
                "Annualized return (CAGR)",
                f"{c['annual_ret']:+.1%}",
                f"{bench_cagr:+.1%}",
                "Compound annual growth actually earned over the period — geometric, "
                "so volatility does not inflate it.",
            ),
            (
                "Annual volatility",
                f"{c['annual_vol']:.1%}",
                f"{bench_vol:.1%}",
                interpret_volatility(c["annual_vol"], universe_vols_report),
            ),
            (
                "Sharpe ratio",
                f"{report_sharpe:.2f}",
                f"{bench_sharpe:.2f}",
                interpret_sharpe(report_sharpe),
            ),
            (
                "Sortino ratio",
                f"{report_sortino:.2f}",
                f"{bench_sortino:.2f}",
                interpret_sortino(report_sortino, report_sharpe),
            ),
            (
                "Max drawdown",
                f"{c['drawdown']:.1%}",
                f"{bench_dd:.1%}",
                interpret_drawdown(c["drawdown"]),
            ),
            (
                "VaR 95% (1 day)",
                f"{c['var_95']:.1%}",
                f"{bench_var:.1%}",
                f"On 95% of days you did not lose more than {eur(total * c['var_95'])} "
                "(historical percentile, no normality assumed).",
            ),
            (
                "Expected shortfall 95%",
                f"{pf_es:.1%}",
                f"{bench_es:.1%}",
                f"Average loss on the worst 5% of days ({eur(total * pf_es)}): what a bad "
                "day costs when it goes beyond the VaR threshold.",
            ),
            (
                f"Beta vs {BENCHMARK}",
                f"{c['beta']:.2f}",
                "—",
                interpret_beta(c["beta"], BENCHMARK),
            ),
            (
                f"Alpha vs {BENCHMARK}",
                f"{c['alpha']:+.1%}/yr",
                "—",
                "Annual excess return not explained by benchmark moves (OLS on daily data).",
            ),
            (
                "Average correlation",
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
                "text": f"Observed annual volatility {c['annual_vol']:.1%} vs the "
                f"{profile_band:.0%} threshold declared for a {risk_profile.lower()} "
                "profile.",
            }
        # allocazione settoriale pesata per capitale (dai profili Yahoo Finance)
        report_sectors = None
        if "sector" in c["fund"].columns:
            sector_by_ticker = (
                c["fund"]["sector"].reindex(list(amounts)).fillna("Not classified")
            )
            report_sectors = (
                (pd.Series(amounts, dtype=float) / total).groupby(sector_by_ticker).sum()
            )
        # copertura dati: titoli con storico più corto della finestra selezionata
        window_start = c["prices"].index[0]
        report_coverage = []
        for t in sorted(amounts):
            first_price = c["prices"][t].first_valid_index()
            if first_price is not None and (first_price - window_start).days > 7:
                report_coverage.append(
                    f"{t} priced only from {pd.Timestamp(first_price):%d/%m/%Y} — its "
                    "metrics use the shorter overlap"
                )
        top_ticker_report = max(amounts, key=amounts.get)
        try:
            shock_report = simulate_shock(c["returns"], portfolio, top_ticker_report, -0.20)
            report_scenario = {
                "label": f"{top_ticker_report} (your largest position, "
                f"{amounts[top_ticker_report] / total:.0%} of capital) drops 20%",
                "direct": shock_report["direct"],
                "total": shock_report["total"],
            }
        except ValueError:
            report_scenario = None
        st.download_button(
            "Download PDF report",
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
                names=st.session_state.get("names", {}),
                advisor=advisor if advisor != DEV_ADVISOR else None,
                risk_profile=risk_profile,
                benchmark=BENCHMARK,
                currency_note=(
                    "amounts in EUR, currency effect included"
                    if in_eur
                    else "amounts in original currencies"
                ),
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
            ),
            file_name=f"portfolio_report_{pd.Timestamp.now():%Y%m%d}.pdf",
            mime="application/pdf",
            width="stretch",
            type="primary",
        )
    with col_log:
        if st.button("Save to history", width="stretch"):
            log_analysis(
                advisor,
                portfolio_name,
                period,
                total,
                c["cum_return"],
                c["risk_score"],
                health=c["health"],
            )
            st.toast("Analysis saved")
    with col_hist:
        history = load_analyses(advisor)
        if not history.empty:
            with st.expander(f"Analysis history ({len(history)})"):
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
                        f'Health Score of "{portfolio_name}" over time: '
                        f"{delta_h:+d} points since the first saved analysis."
                    )
                st.dataframe(
                    history,
                    column_config={
                        "timestamp": st.column_config.TextColumn("Date"),
                        "portfolio": st.column_config.TextColumn("Portfolio"),
                        "period": st.column_config.TextColumn("Period"),
                        "invested": st.column_config.NumberColumn("Invested", format="%.0f €"),
                        "cum_return": st.column_config.NumberColumn("Return", format="percent"),
                        "risk_score": st.column_config.NumberColumn("Risk /100"),
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

    sec("Return")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Invested", eur(total))
    m2.metric(
        "Annualized return (compound)",
        eur(total * c["annual_ret"]),
        delta=f"{c['annual_ret']:+.1%}",
        help="CAGR over the observed period: does not overstate under volatility.",
    )
    m3.metric("Sharpe ratio", f"{sharpe:.2f}", help=f"Computed with risk-free {risk_free:.1%}.")
    m3.caption(interpret_sharpe(sharpe))
    m4.metric("Sortino ratio", f"{sortino:.2f}")
    m4.caption(interpret_sortino(sortino, sharpe))

    sec("Risk")
    r1, r2, r3, r4 = st.columns(4)
    r1.metric(
        "Typical 1-year swing",
        f"± {eur(total * c['annual_vol'])}",
        delta=f"{c['annual_vol']:.1%}",
        delta_color="off",
    )
    r1.caption(interpret_volatility(c["annual_vol"], universe_vols))
    r2.metric("Max historical drop", f"{c['drawdown']:.1%}")
    r2.caption(interpret_drawdown(c["drawdown"]))
    r3.metric("95% VaR (1 day)", eur(total * c["var_95"]))
    r3.caption("On 95% of historical days you did not lose more than this.")
    r4.metric(
        f"Beta vs {BENCHMARK}",
        f"{c['beta']:.2f}",
        delta=f"α {c['alpha']:+.1%}/yr",
        delta_color="off",
    )
    r4.caption(interpret_beta(c["beta"], BENCHMARK))
    st.caption("Estimates based on historical performance: not a forecast.")

    sec(f"Portfolio vs Nasdaq-100 ({BENCHMARK}) · base 100")
    bench_value = (1 + c["bench_daily"]).cumprod()
    st.altair_chart(
        benchmark_overlay(c["pf_value"], bench_value, BENCHMARK),
        width="stretch",
    )
    excess = c["cum_return"] - float(bench_value.iloc[-1] - 1)
    st.caption(
        f"Over the period you did **{excess:+.1%}** versus the Nasdaq-100"
        + (" (net of the EUR/USD rate)." if in_eur else ".")
    )

    col_dd, col_hist = st.columns(2, gap="large")
    with col_dd:
        sec("How far below the peak (drawdown)")
        st.altair_chart(underwater_chart(c["pf_value"]), width="stretch")
        st.caption("Every dip below zero is time spent at a loss versus the prior peak.")
    with col_hist:
        sec("Distribution of days")
        st.altair_chart(returns_histogram(c["pf_daily"], c["var_95"]), width="stretch")
        st.caption(
            "Each bar counts the days with that return. The red line is the "
            "95% VaR: only 5% of days were worse."
        )

    if len(c["pf_daily"]) >= 80:
        col_rvol, col_rbeta = st.columns(2, gap="large")
        with col_rvol:
            sec("Annualized volatility · 60-day rolling")
            rolling_vol = (c["pf_daily"].rolling(60).std() * TRADING_DAYS**0.5).dropna()
            st.altair_chart(simple_line(rolling_vol), width="stretch")
            st.caption("How the portfolio's riskiness changed over time.")
        with col_rbeta:
            sec(f"Beta vs {BENCHMARK} · 60-day rolling")
            aligned = pd.concat({"pf": c["pf_daily"], "bench": c["bench_daily"]}, axis=1).dropna()
            rolling_beta = (
                aligned["pf"].rolling(60).cov(aligned["bench"])
                / aligned["bench"].rolling(60).var()
            ).dropna()
            st.altair_chart(
                simple_line(rolling_beta, color=PALETTE[0], y_format=".1f"),
                width="stretch",
            )
            st.caption("Above 1 you amplify the market, below 1 you dampen it.")

    col_contrib, col_alloc = st.columns([1.3, 1], gap="large")
    with col_contrib:
        sec("Who drove the result (in euros)")
        cum_by_ticker = per_ticker_cumulative_return(c["prices"])
        contributions_eur = pd.Series(
            {t: amounts[t] * float(cum_by_ticker.get(t, 0.0)) for t in amounts}
        )
        st.altair_chart(contribution_bars(contributions_eur), width="stretch")
        st.caption(
            "Invested amount × stock return (constant weights): "
            "the sum roughly reconstructs the total result."
        )
    with col_alloc:
        sec("Distribution")
        st.altair_chart(allocation_bars(amounts), width="stretch")

    sec("€100 in each stock")
    normalized = c["prices"] / c["prices"].iloc[0] * 100
    st.line_chart(normalized, color=PALETTE[: len(normalized.columns)], height=300)

# ================================================================ VISUAL
elif view == "Visual":
    c = computed
    col_ai, col_radar = st.columns([1.3, 1], gap="large")
    with col_ai:
        sec("Automatic analysis")
        insights = generate_insights(
            period,
            c["cum_return"],
            c["contributions"],
            c["avg_corr"],
            c["drawdown"],
            c["beta"],
            BENCHMARK,
        )
        for insight in insights:
            st.markdown(insight)
        st.caption("Generated by deterministic rules on your data, not by a model.")
    with col_radar:
        sec("Risk radar")
        st.altair_chart(radar_chart(c["radar"]), width="stretch")

    col_galaxy, col_timeline = st.columns([1.15, 1], gap="large")
    with col_galaxy:
        sec("Your galaxy")
        st.caption("Size = weight · color = return · proximity = correlation")
        if len(amounts) >= 2:
            corr = correlation_matrix(c["returns"], min_periods=c["min_periods"])
            weights_s = pd.Series({p["ticker"]: p["weight"] for p in portfolio})
            st.altair_chart(
                galaxy_chart(corr, weights_s, per_ticker_cumulative_return(c["prices"])),
                width="stretch",
            )
        else:
            st.info("At least 2 stocks are needed.")
    with col_timeline:
        sec("Month by month")
        monthly = monthly_returns(c["pf_daily"])
        if len(monthly) >= 2:
            st.altair_chart(monthly_bars(monthly), width="stretch")
            best, worst = monthly.idxmax(), monthly.idxmin()
            st.caption(
                f"Best month: **{best.strftime('%b %Y')}** ({monthly.max():+.1%}) "
                f"· worst: **{worst.strftime('%b %Y')}** ({monthly.min():+.1%})"
            )
        else:
            st.info("Period too short for the monthly view.")

    if len(amounts) >= 2:
        col_wr, col_wr_txt = st.columns([1.5, 1], gap="large")
        with col_wr:
            sec("Invested weight vs risk contribution")
            weights_series_ui = pd.Series({p["ticker"]: p["weight"] for p in portfolio})
            st.altair_chart(
                weight_vs_risk_bars(weights_series_ui, c["contributions"]),
                width="stretch",
            )
        with col_wr_txt:
            sec("How to read it")
            top_c = c["contributions"].index[0]
            gap = float(c["contributions"].iloc[0] - weights_series_ui.get(top_c, 0))
            st.markdown(
                f"When the amber bar exceeds the blue one, the stock weighs on "
                f"risk **more than it weighs on capital**. "
                f"Today **{top_c}** drives "
                f"**{c['contributions'].iloc[0]:.0%}** of risk "
                f"({gap:+.0%} versus its weight)."
            )
            st.caption(
                "Marginal contribution to portfolio variance: it accounts for "
                "volatility and correlations, not just the invested amount."
            )

    sec('"What if?" simulator')
    col_sim_in, col_sim_out = st.columns([1, 2], gap="large")
    with col_sim_in:
        sim_ticker = st.selectbox("If this stock...", sorted(amounts))
        shock_pct = st.slider("...moved by", -50, 50, -20, step=5, format="%d%%")
    with col_sim_out:
        impact = simulate_shock(c["returns"], portfolio, sim_ticker, shock_pct / 100)
        s1, s2, s3 = st.columns(3)
        s1.metric("Portfolio today", eur(total))
        s2.metric(
            "After the shock (with contagion)",
            eur(total * (1 + impact["total"])),
            delta=f"{impact['total']:+.1%}",
        )
        s3.metric(
            "Direct effect only",
            eur(total * (1 + impact["direct"])),
            delta=f"{impact['direct']:+.1%}",
            delta_color="off",
        )
        st.caption(
            "Contagion estimates how the other holdings would react, "
            "using their historical betas toward the shocked stock."
        )

# ================================================================ OTTIMIZZA
elif view == "Ottimizza":
    c = computed
    if len(amounts) < 2:
        st.info("At least 2 stocks are needed for optimization.")
    else:
        sec("Markowitz efficient frontier")
        st.caption(
            "For each level of risk, the best return achievable by combining "
            "your holdings (expected returns = historical arithmetic means, "
            "Markowitz convention)."
        )
        returns = c["returns"]
        candidates = {
            "Current": pd.Series({p["ticker"]: p["weight"] for p in portfolio}),
            "Minimum risk": minimum_variance_weights(returns),
            "Maximum Sharpe": max_sharpe_weights(returns, risk_free_rate=risk_free),
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
            st.markdown("**Comparison**")
            compare = points.set_index("nome")
            compare["sharpe"] = (compare["annual_return"] - risk_free) / compare[
                "annual_volatility"
            ]
            st.dataframe(
                compare,
                column_config={
                    "annual_return": st.column_config.NumberColumn("Return", format="percent"),
                    "annual_volatility": st.column_config.NumberColumn(
                        "Volatility", format="percent"
                    ),
                    "sharpe": st.column_config.NumberColumn("Sharpe", format="%.2f"),
                },
            )
            st.markdown("**Suggested weights**")
            st.dataframe(
                pd.DataFrame(candidates),
                column_config={
                    col: st.column_config.NumberColumn(col, format="percent") for col in candidates
                },
            )

# ================================================================ CORRELAZIONI
elif view == "Correlazioni":
    sec("Which stocks move together")
    st.caption(
        "Correlation of daily returns: **+1** = identical, **0** = independent, **-1** = opposite."
    )
    all_prices = market_db_required("corr")
    if all_prices is None:
        st.info("The Nasdaq-100 database is required: run `python download_nasdaq100.py`.")
    else:
        col_sel, col_per = st.columns([2, 1])
        with col_sel:
            corr_ticker = st.selectbox(
                "Reference stock",
                sorted(all_prices.columns),
                index=None,
                placeholder="Choose a Nasdaq-100 stock...",
            )
        with col_per:
            corr_period = st.selectbox("Period", list(PERIOD_DAYS), index=2, key="corr_period")
        if corr_ticker:
            cutoff = all_prices.index[-1] - pd.Timedelta(days=PERIOD_DAYS[corr_period])
            window_returns = compute_daily_returns(all_prices.loc[all_prices.index >= cutoff])
            mp = max(15, min(60, len(window_returns) // 2))
            corr = correlations_with(window_returns, corr_ticker, min_periods=mp)

            col_top, col_bottom = st.columns(2, gap="large")
            with col_top:
                st.markdown(f"**Move TOGETHER with {corr_ticker}**")
                st.altair_chart(correlation_bars(corr.head(10)), width="stretch")
            with col_bottom:
                st.markdown(f"**INDEPENDENT or OPPOSITE to {corr_ticker}**")
                st.altair_chart(correlation_bars(corr.tail(10).sort_values()), width="stretch")

    if computed is not None and len(amounts) >= 2:
        sec("Your portfolio diversification")
        pf_corr = correlation_matrix(computed["returns"], min_periods=computed["min_periods"])
        avg_corr = computed["avg_corr"]
        pairs = pf_corr.where(
            pd.DataFrame(
                [[i < j for j in range(len(pf_corr))] for i in range(len(pf_corr))],
                index=pf_corr.index,
                columns=pf_corr.columns,
            )
        ).stack()

        col_metric, col_heat = st.columns([1, 2], gap="large")
        with col_metric:
            st.metric("Average correlation", f"{avg_corr:.2f}")
            if avg_corr > 0.6:
                st.warning(interpret_correlation(avg_corr))
            elif avg_corr > 0.3:
                st.info(interpret_correlation(avg_corr))
            else:
                st.success(interpret_correlation(avg_corr))
            if len(pairs):
                tightest = pairs.idxmax()
                st.caption(
                    f"Tightest pair: **{tightest[0]} – {tightest[1]}** ({pairs.max():+.2f})"
                )
        with col_heat:
            st.altair_chart(correlation_heatmap(pf_corr), width="stretch")

# ================================================================ FONDAMENTALI
elif view == "Fondamentali":
    sec("Revenue, margins, debt, growth and multiples")
    default_tickers = " ".join(sorted(amounts)) if amounts else "AAPL MSFT NVDA"
    tickers_text = st.text_input("Tickers separated by spaces", default_tickers)
    fund_tickers = tuple(t.upper() for t in tickers_text.split())

    if fund_tickers:
        try:
            data = cached_fundamentals(fund_tickers)
            st.dataframe(
                data,
                column_config={
                    "name": st.column_config.TextColumn("Name"),
                    "sector": st.column_config.TextColumn("Sector"),
                    "dividend_yield": st.column_config.NumberColumn("Div. yield", format="%.2f%%"),
                    "revenue": st.column_config.NumberColumn("Revenue (TTM)", format="compact"),
                    "net_income": st.column_config.NumberColumn(
                        "Net income (TTM)", format="compact"
                    ),
                    "gross_margin": st.column_config.NumberColumn(
                        "Gross margin", format="percent"
                    ),
                    "operating_margin": st.column_config.NumberColumn(
                        "Operating margin", format="percent"
                    ),
                    "net_margin": st.column_config.NumberColumn("Net margin", format="percent"),
                    "total_debt": st.column_config.NumberColumn("Debt", format="compact"),
                    "debt_to_equity": st.column_config.NumberColumn(
                        "Debito/Equity", format="%.1f"
                    ),
                    "revenue_growth": st.column_config.NumberColumn(
                        "Revenue growth", format="percent"
                    ),
                    "earnings_growth": st.column_config.NumberColumn(
                        "Earnings growth", format="percent"
                    ),
                    "pe": st.column_config.NumberColumn("P/E", format="%.1f"),
                    "forward_pe": st.column_config.NumberColumn("P/E fwd", format="%.1f"),
                    "ev_ebitda": st.column_config.NumberColumn("EV/EBITDA", format="%.1f"),
                    "ps": st.column_config.NumberColumn("P/S", format="%.1f"),
                },
            )

            sec("Stock card")
            card_ticker = st.selectbox("Stock", list(data.index))
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
                    "Overall score",
                    f"{overall:.0f}/100",
                    help="Weighted average: Growth 35%, Quality 35%, Valuation 20%, "
                    "low risk 10%. Heuristic, not investment advice.",
                )
                st.caption(f"Annual volatility: {card_vol:.0%}")
        except ValueError as exc:
            st.error(f"{exc}")

# ================================================================ MERCATO
elif view == "Mercato":
    sec("The 103 Nasdaq-100 constituents compared")
    all_prices = market_db_required("mercato")
    if all_prices is None:
        st.info("Database not downloaded yet: run `python download_nasdaq100.py`.")
    else:
        ndx_period = st.selectbox("Comparison period", list(PERIOD_DAYS), index=2)
        cutoff = all_prices.index[-1] - pd.Timedelta(days=PERIOD_DAYS[ndx_period])
        window = all_prices.loc[all_prices.index >= cutoff]

        stats = (
            pd.DataFrame(
                {
                    "period_return": per_ticker_cumulative_return(window),
                    "annual_volatility": compute_daily_returns(window).std() * TRADING_DAYS**0.5,
                }
            )
            .rename_axis("ticker")
            .reset_index()
        )

        col_scatter, col_table = st.columns([3, 2], gap="large")
        with col_scatter:
            st.markdown(f"**Risk vs return ({ndx_period})** — each dot is a stock")
            st.scatter_chart(
                stats,
                x="annual_volatility",
                y="period_return",
                x_label="Annualized volatility",
                y_label=f"Cumulative return ({ndx_period})",
                color=PALETTE[0],
                height=420,
            )
        with col_table:
            st.markdown("**Full ranking**")
            st.dataframe(
                stats.sort_values("period_return", ascending=False),
                column_config={
                    "ticker": st.column_config.TextColumn("Ticker"),
                    "period_return": st.column_config.NumberColumn(
                        f"Return ({ndx_period})", format="percent"
                    ),
                    "annual_volatility": st.column_config.NumberColumn(
                        "Annual volatility", format="percent"
                    ),
                },
                hide_index=True,
                height=420,
            )
        st.caption(
            "Cumulative return over the period (USD prices). "
            "Refresh the data with `python download_nasdaq100.py`."
        )

        sec("PI Score — multifactor ranking")
        st.caption(
            "Composite score 0-100: **50% 12-1 month momentum** (Jegadeesh & "
            "Titman 1993), **30% low volatility** (Baker et al. 2011), "
            "**20% trend** (distance from the 200-day average). Historical "
            "regularities documented in the literature, not guarantees — and "
            "not investment advice."
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
                    "Low volatility", min_value=0, max_value=100, format="%.0f"
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
    sec("What if you had followed a strategy?")
    st.caption(
        "Quarterly rebalancing, weights computed only on prior data "
        "(no look-ahead). Limits: no transaction costs, USD prices, "
        "universe = CURRENT Nasdaq-100 constituents (survivorship bias)."
    )
    all_prices = market_db_required("backtest")
    if all_prices is None:
        st.info("The Nasdaq-100 database is required: run `python download_nasdaq100.py`.")
    else:
        options = [
            "Equal-weight Nasdaq-100",
            "Momentum (top 10 at 6 months)",
            "PI Multifactor (top 10)",
        ]
        if len(amounts) >= 2:
            options += [
                "Your portfolio (buy & hold)",
                "Maximum Sharpe on your holdings",
                "Minimum variance on your holdings",
            ]
        chosen = st.multiselect("Strategies to compare", options, default=options[:3])
        col_bt1, col_bt2 = st.columns(2)
        with col_bt1:
            bt_years = st.select_slider("Horizon", ["1 year", "2 years", "5 years"], "5 years")
        with col_bt2:
            cost_bps = st.slider(
                "Transaction costs (bps per rebalance)",
                0,
                50,
                20,
                step=5,
                help="20 bps = 0.20% of traded value: realistic for retail on liquid "
                "stocks. Buy & hold pays only the initial purchase.",
            )
        cutoff = all_prices.index[-1] - pd.Timedelta(days=PERIOD_DAYS[bt_years])
        window = all_prices.loc[all_prices.index >= cutoff]

        if chosen:
            with st.spinner("Running the backtests..."):
                curves = {}
                try:
                    if "Equal-weight Nasdaq-100" in chosen:
                        curves["Equal-weight Nasdaq-100"] = run_backtest(
                            window, equal_weight, cost_bps=cost_bps
                        )
                    if "Momentum (top 10 at 6 months)" in chosen:
                        curves["Momentum (top 10 at 6 months)"] = run_backtest(
                            window,
                            lambda w: momentum_top(w, top_n=10),
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
                                {"1 year": "1y", "2 years": "2y", "5 years": "5y"}[bt_years],
                            )
                        )
                        weights_now = pd.Series(amounts) / sum(amounts.values())
                        if "Your portfolio (buy & hold)" in chosen:
                            curves["Your portfolio (buy & hold)"] = buy_and_hold(
                                my_prices, weights_now
                            )
                        if "Maximum Sharpe on your holdings" in chosen:
                            curves["Maximum Sharpe on your holdings"] = run_backtest(
                                my_prices, max_sharpe, cost_bps=cost_bps
                            )
                        if "Minimum variance on your holdings" in chosen:
                            curves["Minimum variance on your holdings"] = run_backtest(
                                my_prices, min_variance, cost_bps=cost_bps
                            )
                except ValueError as exc:
                    st.error(f"{exc}")

            if curves:
                equity = pd.DataFrame(curves).dropna(how="all")
                cols = st.columns(len(curves))
                for col, (name, curve) in zip(cols, curves.items(), strict=False):
                    col.metric(name, f"{curve.iloc[-1] / 100 - 1:+.0%}")
                st.line_chart(equity, color=PALETTE[: len(curves)], height=380)

                strategy_stats = pd.DataFrame(
                    [
                        {
                            "Strategy": name,
                            "Return": curve.iloc[-1] / 100 - 1,
                            "Annual volatility": curve.pct_change().std() * TRADING_DAYS**0.5,
                            "Max drawdown": float((curve / curve.cummax() - 1).min()),
                        }
                        for name, curve in curves.items()
                    ]
                )
                st.dataframe(
                    strategy_stats,
                    column_config={
                        "Return": st.column_config.NumberColumn(format="percent"),
                        "Annual volatility": st.column_config.NumberColumn(format="percent"),
                        "Max drawdown": st.column_config.NumberColumn(format="percent"),
                    },
                    hide_index=True,
                    width="stretch",
                )
                st.caption(
                    f"Base-100 curves, {cost_bps} bps cost per rebalance. "
                    "Return isn't everything: look at volatility and drawdown."
                )

# ================================================================ CLIENTI
elif view == "Clients":
    sec("Advisor view — all saved portfolios")
    st.caption(
        "Each saved portfolio is a client: status light, value, Health Score "
        "and the most urgent problem at a glance. To open one: "
        "sidebar → Saved portfolios → Load."
    )

    @st.cache_data(ttl=900, show_spinner=False)
    def quick_client_analysis(items: tuple, period_key: str, eur_flag: bool) -> dict:
        amounts_c = dict(items)
        total_c = sum(amounts_c.values())
        pf_c = [{"ticker": t, "weight": a / total_c} for t, a in amounts_c.items()]
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
            "problem": problems_c[0].replace("**", "")
            if problems_c
            else "No problems flagged by the monitored rules.",
        }

    book = list_portfolios(advisor)
    if not book:
        empty_state(
            "No clients in the book",
            "Save at least one portfolio (sidebar → Saved portfolios) "
            "to see it appear here with status light and main problem.",
            icon="folder",
        )
    else:
        rows_html = ""
        failures = []
        with st.spinner("Analyzing the client book..."):
            for client_name in sorted(book):
                try:
                    a = quick_client_analysis(
                        tuple(sorted(book[client_name].items())), period, in_eur
                    )
                except ValueError as exc:
                    failures.append(f"{client_name}: {exc}")
                    continue
                color = GAIN if a["health"] >= 67 else AMBER if a["health"] >= 34 else LOSS
                chg_css = "up" if a["cum"] >= 0 else "down"
                rows_html += f"""
                <div class="kpi" style="display:flex;align-items:center;
                     gap:16px;margin-bottom:10px;min-width:100%">
                  <div style="width:10px;height:10px;border-radius:50%;
                       background:{color};flex-shrink:0"></div>
                  <div style="min-width:150px">
                    <div style="font-weight:700">{client_name}</div>
                    <div class="kpi-sub">{eur(a["invested"])} invested ·
                         vol. {a["vol"]:.0%}</div>
                  </div>
                  <div style="min-width:120px">
                    <div class="kpi-sub">VALUE</div>
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
            st.warning(f"Analysis failed — {failure}")
        st.caption(
            f"{len(book)} clients · horizon {period} · "
            + ("EUR values, currency included" if in_eur else "original currencies")
            + " · analyses refreshed every 15 minutes."
        )

# ============================================================ COMPLIANCE FOOTER
compliance_footer()
