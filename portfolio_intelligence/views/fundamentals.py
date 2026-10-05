"""Vista Fondamentali: tabella multipli/margini e scheda titolo con DNA."""

import streamlit as st

from portfolio_intelligence.analytics.insights import stock_scores
from portfolio_intelligence.i18n import t
from portfolio_intelligence.portfolio.returns import compute_daily_returns
from portfolio_intelligence.ui.components import dna_card_html, pct, sec
from portfolio_intelligence.views.common import TRADING_DAYS, cached_fundamentals, cached_prices
from portfolio_intelligence.views.context import ViewContext


def render(ctx: ViewContext) -> None:
    amounts = ctx.amounts

    sec(t("fund.title"))
    default_tickers = " ".join(sorted(amounts)) if amounts else "AAPL MSFT NVDA"
    tickers_text = st.text_input(t("fund.tickers"), default_tickers)
    fund_tickers = tuple(t.upper() for t in tickers_text.split())

    if fund_tickers:
        try:
            data = cached_fundamentals(fund_tickers)
            st.dataframe(
                data,
                column_config={
                    "name": st.column_config.TextColumn(t("fund.name")),
                    "sector": st.column_config.TextColumn(t("fund.sector")),
                    "dividend_yield": st.column_config.NumberColumn(
                        t("fund.div_yield"), format="%.2f%%"
                    ),
                    "revenue": st.column_config.NumberColumn(t("fund.revenue"), format="compact"),
                    "net_income": st.column_config.NumberColumn(
                        t("fund.net_income"), format="compact"
                    ),
                    "gross_margin": st.column_config.NumberColumn(
                        t("fund.gross_margin"), format="percent"
                    ),
                    "operating_margin": st.column_config.NumberColumn(
                        t("fund.op_margin"), format="percent"
                    ),
                    "net_margin": st.column_config.NumberColumn(
                        t("fund.net_margin"), format="percent"
                    ),
                    "total_debt": st.column_config.NumberColumn(t("fund.debt"), format="compact"),
                    "debt_to_equity": st.column_config.NumberColumn(t("fund.de"), format="%.1f"),
                    "revenue_growth": st.column_config.NumberColumn(
                        t("fund.rev_growth"), format="percent"
                    ),
                    "earnings_growth": st.column_config.NumberColumn(
                        t("fund.eps_growth"), format="percent"
                    ),
                    "pe": st.column_config.NumberColumn("P/E", format="%.1f"),
                    "forward_pe": st.column_config.NumberColumn(t("fund.fwd_pe"), format="%.1f"),
                    "ev_ebitda": st.column_config.NumberColumn("EV/EBITDA", format="%.1f"),
                    "ps": st.column_config.NumberColumn("P/S", format="%.1f"),
                    "source": st.column_config.TextColumn(t("fund.source")),
                },
            )
            st.caption(t("fund.caption"))

            sec(t("fund.card"))
            card_ticker = st.selectbox(t("fund.stock"), list(data.index))
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
                    dna_card_html(scores, f"{row['name']}", title=t("fund.dna_title")),
                    unsafe_allow_html=True,
                )
            with col_num:
                st.metric(
                    t("fund.overall"),
                    f"{overall:.0f}/100",
                    help=t("fund.overall_help"),
                )
                st.caption(t("fund.card_vol", vol=pct(card_vol, 0)))
        except ValueError as exc:
            st.error(f"{exc}")
