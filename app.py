"""Dashboard Streamlit per portfolio-intelligence.

Avvio: streamlit run app.py
"""

from pathlib import Path

import pandas as pd
import streamlit as st

from src.analytics import (
    compute_daily_returns,
    per_ticker_annualized_stats,
    portfolio_expected_return,
    portfolio_volatility,
)
from src.fundamentals import fetch_fundamentals
from src.market_data import fetch_price_history
from src.portfolio import weights_sum_to_one

# Palette categorica validata (dataviz skill, light mode)
PALETTE = ["#2a78d6", "#1baf7a", "#eda100", "#008300", "#4a3aa7", "#e34948", "#e87ba4", "#eb6834"]
TRADING_DAYS = 252
NASDAQ100_PRICES = Path("data/nasdaq100_prices.csv")

st.set_page_config(page_title="Portfolio Intelligence", page_icon="📈", layout="wide")
st.title("Portfolio Intelligence")


@st.cache_data(ttl=3600, show_spinner="Scarico i prezzi da Yahoo Finance...")
def cached_prices(tickers: tuple[str, ...], period: str) -> pd.DataFrame:
    return fetch_price_history(list(tickers), period=period)


@st.cache_data(ttl=3600, show_spinner="Scarico i fondamentali da Yahoo Finance...")
def cached_fundamentals(tickers: tuple[str, ...]) -> pd.DataFrame:
    return fetch_fundamentals(list(tickers))


tab_portfolio, tab_fundamentals, tab_nasdaq = st.tabs(
    ["Portafoglio", "Fondamentali", "Nasdaq-100"]
)

with tab_portfolio:
    st.subheader("Rendimento e rischio del portafoglio")

    default_positions = pd.DataFrame(
        {"ticker": ["AAPL", "MSFT", "NVDA"], "weight": [0.4, 0.3, 0.3]}
    )
    col_input, col_period = st.columns([3, 1])
    with col_input:
        positions = st.data_editor(
            default_positions,
            num_rows="dynamic",
            column_config={
                "ticker": st.column_config.TextColumn("Ticker", required=True),
                "weight": st.column_config.NumberColumn(
                    "Peso", min_value=0.0, max_value=1.0, step=0.05, required=True
                ),
            },
            key="positions",
        )
    with col_period:
        period = st.selectbox("Periodo", ["1mo", "6mo", "1y", "2y", "5y"], index=2)

    portfolio = [
        {"ticker": str(row.ticker).upper().strip(), "weight": float(row.weight)}
        for row in positions.itertuples()
        if str(row.ticker).strip()
    ]

    if not portfolio:
        st.info("Aggiungi almeno una posizione.")
    elif not weights_sum_to_one(portfolio):
        total = sum(p["weight"] for p in portfolio)
        st.warning(f"I pesi devono sommare a 1 (attuale: {total:.2f}).")
    else:
        try:
            tickers = tuple(p["ticker"] for p in portfolio)
            prices = cached_prices(tickers, period)
            returns = compute_daily_returns(prices)

            daily_ret = portfolio_expected_return(returns, portfolio)
            daily_vol = portfolio_volatility(returns, portfolio)

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Rendimento giornaliero", f"{daily_ret:.4%}")
            m2.metric("Volatilità giornaliera", f"{daily_vol:.4%}")
            m3.metric("Rendimento annualizzato", f"{daily_ret * TRADING_DAYS:.2%}")
            m4.metric("Volatilità annualizzata", f"{daily_vol * TRADING_DAYS**0.5:.2%}")

            st.markdown("**Prezzi normalizzati (base 100)**")
            normalized = prices / prices.iloc[0] * 100
            st.line_chart(normalized, color=PALETTE[: len(normalized.columns)])
        except ValueError as exc:
            st.error(f"{exc}")

with tab_fundamentals:
    st.subheader("Ricavi, margini, debito, crescita e multipli")

    tickers_text = st.text_input("Ticker separati da spazio", "AAPL MSFT NVDA")
    tickers = tuple(t.upper() for t in tickers_text.split())

    if tickers:
        try:
            data = cached_fundamentals(tickers)
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
        except ValueError as exc:
            st.error(f"{exc}")

with tab_nasdaq:
    st.subheader("Rendimento e volatilità dei componenti Nasdaq-100 (5 anni)")

    if not NASDAQ100_PRICES.exists():
        st.info(
            "Database non ancora scaricato: esegui `python download_nasdaq100.py` dal terminale."
        )
    else:
        prices = pd.read_csv(NASDAQ100_PRICES, index_col=0, parse_dates=True)
        stats = per_ticker_annualized_stats(compute_daily_returns(prices))
        stats = stats.rename_axis("ticker").reset_index()

        st.markdown("**Rischio vs rendimento** — ogni punto è un titolo")
        st.scatter_chart(
            stats,
            x="annual_volatility",
            y="annual_return",
            x_label="Volatilità annualizzata",
            y_label="Rendimento annualizzato",
            color=PALETTE[0],
        )

        st.markdown("**Classifica completa**")
        st.dataframe(
            stats.sort_values("annual_return", ascending=False),
            column_config={
                "ticker": st.column_config.TextColumn("Ticker"),
                "annual_return": st.column_config.NumberColumn("Rendimento annuo", format="percent"),
                "annual_volatility": st.column_config.NumberColumn(
                    "Volatilità annua", format="percent"
                ),
            },
            hide_index=True,
        )
