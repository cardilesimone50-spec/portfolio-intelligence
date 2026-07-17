"""Sidebar: identità advisor, gestione posizioni, import, portafogli, settings."""

from dataclasses import dataclass

import streamlit as st

from src.data.importers import parse_positions
from src.i18n import t
from src.data.store import list_portfolios, save_portfolio
from src.ui.components import empty_state, eur, position_card_html, sec, ticker_preview_html
from src.ui.identity import auth_configured, is_authenticated
from src.views.common import cached_risk_free, known_tickers, language_selector, ticker_preview
from src.visualization.charts import PALETTE


@dataclass
class SidebarSettings:
    portfolio_name: str
    period: str
    in_eur: bool
    risk_free: float
    risk_profile: str


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


def render_sidebar(advisor: str) -> SidebarSettings:
    """Disegna la sidebar e restituisce le impostazioni scelte."""
    with st.sidebar:
        st.markdown(
            '<div class="brand" style="font-size:.9rem">◆ SMARTEE<b>FINANCE</b></div>',
            unsafe_allow_html=True,
        )

        language_selector("lang_sidebar")

        # identità consulente + login/logout (B2B multi-tenant)
        if auth_configured():
            if is_authenticated():
                st.caption(t("side.advisor", advisor=advisor))
                if st.button(t("side.logout"), width="stretch"):
                    st.logout()
            else:
                st.caption(t("side.login_hint"))
                if st.button(t("side.login"), type="primary", width="stretch"):
                    st.login()
        else:
            st.caption(t("side.advisor_demo", advisor=advisor))

        sec(t("side.add_stock"))

        new_ticker = st.selectbox(
            "Search stock",
            known_tickers(),
            index=None,
            placeholder=t("gate.search_placeholder"),
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
                st.button(t("gate.add"), width="stretch", type="primary", on_click=_add_holding)
        else:
            st.caption(t("side.search_hint"))

        sec(t("side.your_holdings"))

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
                        t("side.amount"),
                        min_value=0.0,
                        value=float(amount),
                        step=500.0,
                        key=f"edit_{ticker}",
                    )
                    col_ok, col_del = st.columns(2)
                    if col_ok.button(t("side.save"), key=f"save_{ticker}", width="stretch"):
                        if updated > 0:
                            st.session_state.holdings[ticker] = float(updated)
                        else:
                            st.session_state.holdings.pop(ticker, None)
                        st.rerun()
                    if col_del.button(t("side.remove"), key=f"del_{ticker}", width="stretch"):
                        st.session_state.holdings.pop(ticker, None)
                        st.rerun()
            st.caption(t("gate.total", total=eur(total), n=len(holdings)))
        else:
            empty_state(t("side.empty_title"), t("side.empty_hint"), icon="folder")

        with st.expander(t("side.import")):
            uploaded = st.file_uploader(
                t("side.upload_label"),
                type=["csv", "xlsx", "xls"],
                help=t("side.upload_help"),
            )
            if uploaded is not None:
                file_id = f"{uploaded.name}-{uploaded.size}"
                if st.session_state.get("last_upload") != file_id:
                    try:
                        st.session_state.holdings = parse_positions(
                            uploaded.getvalue(), uploaded.name
                        )
                        st.session_state.last_upload = file_id
                        st.toast(t("side.imported", n=len(st.session_state.holdings)))
                        st.rerun()
                    except ValueError as exc:
                        st.error(t("side.import_failed", err=exc))

        saved = list_portfolios(advisor)
        with st.expander(t("side.saved_portfolios")):
            portfolio_name = st.text_input(t("side.name"), value="My portfolio")
            if st.button(t("side.save_composition"), width="stretch") and holdings:
                save_portfolio(advisor, portfolio_name, holdings)
                st.toast(t("side.saved_toast", name=portfolio_name))
            if saved:
                selected_saved = st.selectbox(
                    t("side.load"), sorted(saved), index=None,
                    placeholder=t("side.load_placeholder"),
                )
                if selected_saved and st.button(t("side.load_btn"), width="stretch"):
                    st.session_state.holdings = dict(saved[selected_saved])
                    st.rerun()

        with st.expander(t("side.settings")):
            period = st.selectbox(
                t("side.horizon"), ["1mo", "6mo", "1y", "2y", "5y"], index=2, key="pf_period"
            )
            in_eur = st.toggle(
                t("side.in_eur"),
                value=True,
                help=t("side.in_eur_help"),
            )
            rf_baseline_pct = min(10.0, max(0.0, round(cached_risk_free() * 100, 2)))
            risk_free = (
                st.number_input(
                    t("side.risk_free"),
                    min_value=0.0,
                    max_value=10.0,
                    value=rf_baseline_pct,
                    step=0.25,
                    help=t("side.risk_free_help"),
                )
                / 100
            )
            st.caption(t("side.risk_free_caption", rate=f"{rf_baseline_pct:.2f}"))
            risk_profile = st.selectbox(
                t("side.risk_profile"),
                ["Not set", "Conservative", "Moderate", "Aggressive"],
                index=0,
                format_func=lambda p: t(f"prof.{p}"),
                help=t("side.risk_profile_help"),
            )

    return SidebarSettings(
        portfolio_name=portfolio_name,
        period=period,
        in_eur=in_eur,
        risk_free=risk_free,
        risk_profile=risk_profile,
    )
