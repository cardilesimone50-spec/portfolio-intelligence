"""Dashboard Streamlit per portfolio-intelligence.

Avvio: streamlit run app.py
"""

from pathlib import Path

import altair as alt
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

# Palette categorica validata (dataviz skill, light mode)
PALETTE = ["#2a78d6", "#1baf7a", "#eda100", "#008300", "#4a3aa7", "#e34948", "#e87ba4", "#eb6834"]
TRADING_DAYS = 252
NASDAQ100_PRICES = Path("data/nasdaq100_prices.csv")

st.set_page_config(page_title="Portfolio Intelligence", page_icon="📈", layout="wide")

st.markdown(
    """
    <style>
    [data-testid="stMetric"] {
        background: rgba(42, 120, 214, 0.07);
        border: 1px solid rgba(128, 128, 128, 0.18);
        border-radius: 14px;
        padding: 18px 20px;
    }
    [data-testid="stMetricLabel"] { opacity: 0.75; }
    .block-container { padding-top: 2.2rem; }
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


# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.header("Il tuo portafoglio")
    st.caption("Inserisci quanto investi su ogni titolo, in euro.")

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
    period = st.selectbox("Orizzonte storico", ["1mo", "6mo", "1y", "2y", "5y"], index=2)
    st.caption("Dati di mercato: Yahoo Finance")

amounts = {
    str(row.ticker).upper().strip(): float(row.importo)
    for row in positions.itertuples()
    if str(row.ticker).strip() and float(row.importo or 0) > 0
}
total = sum(amounts.values())
portfolio = [{"ticker": t, "weight": amount / total} for t, amount in amounts.items()] if total else []

# ---------------------------------------------------------------- main
st.title("Portfolio Intelligence")

tab_portfolio, tab_fundamentals, tab_nasdaq = st.tabs(
    ["📊  Andamento", "🏢  Fondamentali", "🏆  Nasdaq-100"]
)

with tab_portfolio:
    if not portfolio:
        st.info("Aggiungi almeno un titolo con un importo positivo nella barra laterale.")
    else:
        try:
            tickers = tuple(sorted(amounts))
            prices = cached_prices(tickers, period)
            returns = compute_daily_returns(prices)

            annual_ret = portfolio_expected_return(returns, portfolio) * TRADING_DAYS
            annual_vol = portfolio_volatility(returns, portfolio) * TRADING_DAYS**0.5

            m1, m2, m3 = st.columns(3)
            m1.metric("Investimento", eur(total))
            m2.metric(
                "Guadagno atteso in 1 anno",
                eur(total * annual_ret),
                delta=f"{annual_ret:+.1%}",
            )
            m3.metric(
                "Oscillazione tipica in 1 anno",
                f"± {eur(total * annual_vol)}",
                delta=f"{annual_vol:.1%}",
                delta_color="off",
            )
            st.caption(
                "Stime basate sull'andamento storico del periodo selezionato: "
                "non sono una previsione."
            )

            col_alloc, col_chart = st.columns([2, 3])

            with col_alloc:
                st.markdown("**Come sono distribuiti i tuoi soldi**")
                alloc = pd.DataFrame(
                    {"ticker": list(amounts), "importo": list(amounts.values())}
                )
                base = alt.Chart(alloc).encode(
                    y=alt.Y("ticker:N", sort="-x", title=None),
                    x=alt.X("importo:Q", title=None, axis=None),
                )
                bars = base.mark_bar(cornerRadiusEnd=4, height=22).encode(
                    color=alt.Color(
                        "ticker:N",
                        scale=alt.Scale(domain=sorted(amounts), range=PALETTE),
                        legend=None,
                    )
                )
                labels = base.mark_text(align="left", dx=6).encode(
                    text=alt.Text("importo:Q", format=",.0f")
                )
                st.altair_chart(
                    (bars + labels).properties(height=42 * len(alloc) + 20),
                    use_container_width=True,
                )

            with col_chart:
                st.markdown("**Se avessi investito 100 € in ciascun titolo**")
                normalized = prices / prices.iloc[0] * 100
                st.line_chart(
                    normalized,
                    color=PALETTE[: len(normalized.columns)],
                    height=300,
                )
        except ValueError as exc:
            st.error(f"{exc}")

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

        col_scatter, col_table = st.columns([3, 2])

        with col_scatter:
            st.markdown("**Rischio vs rendimento** — ogni punto è un titolo")
            st.scatter_chart(
                stats,
                x="annual_volatility",
                y="annual_return",
                x_label="Volatilità annualizzata",
                y_label="Rendimento annualizzato",
                color=PALETTE[0],
                height=420,
            )

        with col_table:
            st.markdown("**Classifica completa**")
            st.dataframe(
                stats.sort_values("annual_return", ascending=False),
                column_config={
                    "ticker": st.column_config.TextColumn("Ticker"),
                    "annual_return": st.column_config.NumberColumn(
                        "Rendimento annuo", format="percent"
                    ),
                    "annual_volatility": st.column_config.NumberColumn(
                        "Volatilità annua", format="percent"
                    ),
                },
                hide_index=True,
                height=420,
            )
