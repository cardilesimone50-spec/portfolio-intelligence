"""Costanti di dominio e accesso dati cachato condivisi da tutte le viste."""

import pandas as pd
import streamlit as st

from src.data.cache import load_nasdaq100_prices
from src.data.fx import fetch_eurusd
from src.data.rates import fetch_risk_free_rate
from src.data.store import load_prices as load_stored_prices
from src.data.yahoo_client import fetch_price_history
from src.fundamentals.valuation import fetch_fundamentals
from src.i18n import LANGUAGES, set_language
from src.ui.components import empty_state

BENCHMARK = "QQQ"  # ETF sul Nasdaq-100
TRADING_DAYS = 252
PERIOD_DAYS = {"1 mese": 30, "6 mesi": 182, "1 anno": 365, "2 anni": 730, "5 anni": 1826}
# annual volatility thresholds per risk profile (declared in the UI)
PROFILE_VOL = {"Conservative": 0.10, "Moderate": 0.18, "Aggressive": 0.30}
# portafoglio di esempio: quantità, prezzo E data di carico (P&L + IRR demo)
SAMPLE_PORTFOLIO = {
    "AAPL": {"lots": [{"qty": 20.0, "price": 150.0, "date": "2024-11-15"}]},
    "MSFT": {"lots": [{"qty": 8.0, "price": 320.0, "date": "2025-02-10"}]},
    "NVDA": {
        "lots": [
            {"qty": 20.0, "price": 48.0, "date": "2024-09-05"},
            {"qty": 10.0, "price": 84.0, "date": "2025-04-22"},
        ]
    },
}

_FALLBACK_TICKERS = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "AVGO", "COST", "NFLX"]


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


@st.cache_data(ttl=600, show_spinner=False)
def cached_option_chain(ticker: str, kind: str, target_days: int) -> dict | None:
    """Chain di opzioni reale (best-effort, cache 10 minuti); None se non disponibile."""
    from src.data.options_chain import fetch_option_chain

    return fetch_option_chain(ticker, kind, target_days)


def language_selector(key: str) -> None:
    """Selettore EN/IT: persiste in session_state['language'] e rerun al cambio.

    La chiave del widget è separata dal valore persistito, così la scelta
    sopravvive quando il widget non è renderizzato (es. passando dal gate all'app).
    """
    current = st.session_state.get("language", "en")
    codes = list(LANGUAGES)
    choice = st.selectbox(
        "Language",
        codes,
        index=codes.index(current),
        format_func=lambda code: LANGUAGES[code],
        key=key,
        label_visibility="collapsed",
    )
    if choice != current:
        st.session_state.language = choice
        set_language(choice)
        st.rerun()


def known_tickers() -> list[str]:
    """Universo per la ricerca titoli: il DB Nasdaq-100 se c'è, altrimenti i big."""
    db = load_market_db()
    return sorted(db.columns) if db is not None else list(_FALLBACK_TICKERS)
