"""Vista Fondamentali: tabella multipli/margini e scheda titolo con DNA."""

import streamlit as st

from portfolio_intelligence.analytics.insights import stock_scores
from portfolio_intelligence.i18n import t
from portfolio_intelligence.portfolio.returns import compute_daily_returns
from portfolio_intelligence.ui.components import dna_card_html, pct, sec, styled
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
                styled(
                    data,
                    {
                        "dividend_yield": ("pp", 2),
                        "revenue": ("compact",),
                        "net_income": ("compact",),
                        "total_debt": ("compact",),
                        "gross_margin": ("pct", 1, False),
                        "operating_margin": ("pct", 1, False),
                        "net_margin": ("pct", 1, False),
                        "revenue_growth": ("pct", 1, True),
                        "earnings_growth": ("pct", 1, True),
                        "debt_to_equity": ("num", 1),
                        "pe": ("num", 1),
                        "forward_pe": ("num", 1),
                        "ev_ebitda": ("num", 1),
                        "ps": ("num", 1),
                    },
                ),
                column_config={
                    "name": st.column_config.TextColumn(t("fund.name")),
                    "sector": st.column_config.TextColumn(t("fund.sector")),
                    "dividend_yield": st.column_config.NumberColumn(t("fund.div_yield")),
                    "revenue": st.column_config.NumberColumn(t("fund.revenue")),
                    "net_income": st.column_config.NumberColumn(t("fund.net_income")),
                    "gross_margin": st.column_config.NumberColumn(t("fund.gross_margin")),
                    "operating_margin": st.column_config.NumberColumn(t("fund.op_margin")),
                    "net_margin": st.column_config.NumberColumn(t("fund.net_margin")),
                    "total_debt": st.column_config.NumberColumn(t("fund.debt")),
                    "debt_to_equity": st.column_config.NumberColumn(t("fund.de")),
                    "revenue_growth": st.column_config.NumberColumn(t("fund.rev_growth")),
                    "earnings_growth": st.column_config.NumberColumn(t("fund.eps_growth")),
                    "pe": st.column_config.NumberColumn("P/E"),
                    "forward_pe": st.column_config.NumberColumn(t("fund.fwd_pe")),
                    "ev_ebitda": st.column_config.NumberColumn("EV/EBITDA"),
                    "ps": st.column_config.NumberColumn("P/S"),
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
