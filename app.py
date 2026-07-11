"""Dashboard Streamlit per portfolio-intelligence.

Avvio: streamlit run app.py
"""

from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from src.analytics import (
    average_pairwise_correlation,
    compute_daily_returns,
    correlation_matrix,
    correlations_with,
    per_ticker_cumulative_return,
    portfolio_expected_return,
    portfolio_volatility,
)
from src.fundamentals import fetch_fundamentals
from src.market_data import fetch_price_history

# Palette categorica validata (dataviz skill, light mode)
PALETTE = ["#2a78d6", "#1baf7a", "#eda100", "#008300", "#4a3aa7", "#e34948", "#e87ba4", "#eb6834"]
TRADING_DAYS = 252
NASDAQ100_PRICES = Path("data/nasdaq100_prices.csv")
PERIOD_DAYS = {"1 mese": 30, "6 mesi": 182, "1 anno": 365, "2 anni": 730, "5 anni": 1826}
PERIOD_YF = {"1 mese": "1mo", "6 mesi": "6mo", "1 anno": "1y", "2 anni": "2y", "5 anni": "5y"}
# Coppia divergente per la correlazione: blu = opposti, grigio = indipendenti, rosso = insieme
DIVERGING = ["#2a78d6", "#f5f5f2", "#e34948"]

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


st.title("Portfolio Intelligence")

tab_portfolio, tab_corr, tab_fundamentals, tab_nasdaq = st.tabs(
    ["📊  Il mio portafoglio", "🔗  Chi si muove insieme", "🏢  Fondamentali", "🏆  Nasdaq-100"]
)

# ---------------------------------------------------------------- portafoglio
with tab_portfolio:
    col_editor, col_results = st.columns([1, 2.4], gap="large")

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
        st.caption("Aggiungi righe con il +, cancella selezionando la riga. Dati: Yahoo Finance.")

    amounts = {
        str(row.ticker).upper().strip(): float(row.importo)
        for row in positions.itertuples()
        if str(row.ticker).strip() and float(row.importo or 0) > 0
    }
    total = sum(amounts.values())
    portfolio = (
        [{"ticker": t, "weight": amount / total} for t, amount in amounts.items()] if total else []
    )

    with col_results:
        if not portfolio:
            st.info("Aggiungi almeno un titolo con un importo positivo.")
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

                st.markdown("**Come sono distribuiti i tuoi soldi**")
                alloc = pd.DataFrame({"ticker": list(amounts), "importo": list(amounts.values())})
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

                st.markdown("**Se avessi investito 100 € in ciascun titolo**")
                normalized = prices / prices.iloc[0] * 100
                st.line_chart(normalized, color=PALETTE[: len(normalized.columns)], height=320)
            except ValueError as exc:
                st.error(f"{exc}")

# ---------------------------------------------------------------- correlazioni
with tab_corr:
    st.subheader("Quali titoli si muovono insieme")
    st.caption(
        "Correlazione dei rendimenti giornalieri: **+1** = si muovono identici, "
        "**0** = indipendenti, **-1** = opposti. "
        "Titoli molto correlati non diversificano il rischio."
    )

    if not NASDAQ100_PRICES.exists():
        st.info(
            "Serve il database Nasdaq-100: esegui `python download_nasdaq100.py` dal terminale."
        )
    else:
        all_prices = pd.read_csv(NASDAQ100_PRICES, index_col=0, parse_dates=True)

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

            def corr_bars(series: pd.Series, title: str) -> None:
                df = series.rename("corr").rename_axis("ticker").reset_index()
                base = alt.Chart(df).encode(
                    y=alt.Y("ticker:N", sort=None, title=None),
                    x=alt.X("corr:Q", title="Correlazione",
                            scale=alt.Scale(domain=[-1, 1])),
                )
                bars = base.mark_bar(cornerRadiusEnd=4, height=18).encode(
                    color=alt.Color(
                        "corr:Q",
                        scale=alt.Scale(domain=[-1, 0, 1], range=DIVERGING),
                        legend=None,
                    )
                )
                labels = base.mark_text(align="left", dx=6).encode(
                    text=alt.Text("corr:Q", format="+.2f")
                )
                st.markdown(f"**{title}**")
                st.altair_chart(
                    (bars + labels).properties(height=26 * len(df) + 20),
                    use_container_width=True,
                )

            col_top, col_bottom = st.columns(2, gap="large")
            with col_top:
                corr_bars(corr.head(10), f"Si muovono INSIEME a {corr_ticker}")
            with col_bottom:
                corr_bars(
                    corr.tail(10).sort_values(),
                    f"Si muovono in modo INDIPENDENTE o OPPOSTO a {corr_ticker}",
                )

    if len(amounts) >= 2:
        st.divider()
        st.subheader("Diversificazione del tuo portafoglio")
        try:
            pf_period_label = "1 anno"
            pf_prices = cached_prices(tuple(sorted(amounts)), PERIOD_YF[pf_period_label])
            pf_returns = compute_daily_returns(pf_prices)
            pf_min_periods = max(15, min(60, len(pf_returns) // 2))

            avg_corr = average_pairwise_correlation(pf_returns, min_periods=pf_min_periods)
            pf_corr = correlation_matrix(pf_returns, min_periods=pf_min_periods)

            pairs = pf_corr.where(
                pd.DataFrame(
                    [[i < j for j in range(len(pf_corr))] for i in range(len(pf_corr))],
                    index=pf_corr.index, columns=pf_corr.columns,
                )
            ).stack()

            col_metric, col_heat = st.columns([1, 2], gap="large")
            with col_metric:
                st.metric("Correlazione media (1 anno)", f"{avg_corr:.2f}")
                if avg_corr > 0.6:
                    st.warning(
                        "I tuoi titoli si muovono molto insieme: "
                        "se scende uno, tendono a scendere tutti."
                    )
                elif avg_corr > 0.3:
                    st.info("Diversificazione nella media.")
                else:
                    st.success("Buona diversificazione: i titoli si muovono in modo indipendente.")
                if len(pairs):
                    tightest = pairs.idxmax()
                    st.caption(
                        f"Coppia più legata: **{tightest[0]} – {tightest[1]}** "
                        f"({pairs.max():+.2f})"
                    )

            with col_heat:
                heat_df = (
                    pf_corr.rename_axis("a")
                    .reset_index()
                    .melt(id_vars="a", var_name="b", value_name="corr")
                )
                heat = (
                    alt.Chart(heat_df)
                    .mark_rect()
                    .encode(
                        x=alt.X("a:N", title=None),
                        y=alt.Y("b:N", title=None),
                        color=alt.Color(
                            "corr:Q",
                            scale=alt.Scale(domain=[-1, 0, 1], range=DIVERGING),
                            legend=alt.Legend(title="Correlazione"),
                        ),
                    )
                )
                text = (
                    alt.Chart(heat_df)
                    .mark_text()
                    .encode(
                        x="a:N",
                        y="b:N",
                        text=alt.Text("corr:Q", format=".2f"),
                        color=alt.condition(
                            "abs(datum.corr) > 0.6", alt.value("white"), alt.value("black")
                        ),
                    )
                )
                st.altair_chart(
                    (heat + text).properties(height=60 * len(pf_corr) + 40),
                    use_container_width=True,
                )
        except ValueError as exc:
            st.error(f"{exc}")

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
        except ValueError as exc:
            st.error(f"{exc}")

# ---------------------------------------------------------------- nasdaq-100
with tab_nasdaq:
    st.subheader("I 103 componenti del Nasdaq-100 a confronto")

    if not NASDAQ100_PRICES.exists():
        st.info(
            "Database non ancora scaricato: esegui `python download_nasdaq100.py` dal terminale."
        )
    else:
        all_prices = pd.read_csv(NASDAQ100_PRICES, index_col=0, parse_dates=True)

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
            "Rendimento cumulato nel periodo selezionato (non annualizzato). "
            "Aggiorna i dati con `python download_nasdaq100.py`."
        )
