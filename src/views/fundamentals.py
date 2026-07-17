"""Vista Fondamentali: tabella multipli/margini e scheda titolo con DNA."""

import streamlit as st

from src.analytics.insights import stock_scores
from src.portfolio.returns import compute_daily_returns
from src.ui.components import dna_card_html, sec
from src.views.common import TRADING_DAYS, cached_fundamentals, cached_prices
from src.views.context import ViewContext


def render(ctx: ViewContext) -> None:
    amounts = ctx.amounts

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
