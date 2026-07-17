"""Sidebar: identità advisor, gestione posizioni, import, portafogli, settings."""

from dataclasses import dataclass

import streamlit as st

from src.data.importers import parse_positions
from src.i18n import t
from src.portfolio.positions import merge_lot, normalize_portfolio
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
    qty = float(st.session_state.get(f"add_qty_{k}") or 0)
    price = float(st.session_state.get(f"add_price_{k}") or 0)
    if qty <= 0 or price <= 0:
        return
    st.session_state.positions[k] = merge_lot(st.session_state.positions.get(k), qty, price)
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
            preview = ticker_preview(key)
            st.markdown(
                ticker_preview_html(key, color, preview),
                unsafe_allow_html=True,
            )

            default_price = float(preview["price"]) if preview and preview.get("price") else 100.0
            col_qty, col_price = st.columns(2, gap="small")
            with col_qty:
                st.number_input(
                    t("pos.qty"),
                    min_value=0.0001,
                    value=10.0,
                    step=1.0,
                    key=f"add_qty_{key}",
                )
            with col_price:
                st.number_input(
                    t("pos.buy_price"),
                    min_value=0.0001,
                    value=default_price,
                    step=1.0,
                    key=f"add_price_{key}",
                    help=t("pos.current_price") + f": {default_price:,.2f}",
                )
            st.button(t("gate.add"), width="stretch", type="primary", on_click=_add_holding)
        else:
            st.caption(t("side.search_hint"))

        sec(t("side.your_holdings"))

        positions = st.session_state.positions
        costs = {
            ticker: (pos["qty"] * pos["price"] if "qty" in pos else pos.get("amount", 0.0))
            for ticker, pos in positions.items()
        }
        total = sum(costs.values())
        if positions:
            sorted_tickers = sorted(costs, key=costs.get, reverse=True)
            known_names = st.session_state.get("names", {})
            for ticker in sorted_tickers:
                pos = positions[ticker]
                color = PALETTE[sorted(costs).index(ticker) % len(PALETTE)]
                weight = costs[ticker] / total if total else 0
                company = known_names.get(ticker, "")
                label = (
                    f"{pos['qty']:g} × {pos['price']:,.2f}"
                    if "qty" in pos
                    else eur(pos.get("amount", 0.0))
                )
                col_card, col_menu = st.columns([5, 1], gap="small")
                with col_card:
                    st.markdown(
                        position_card_html(
                            ticker, costs[ticker], weight, color, company, amount_label=label
                        ),
                        unsafe_allow_html=True,
                    )
                with col_menu, st.popover("···"):
                    current = pos if "qty" in pos else {"qty": 0.0, "price": 0.0}
                    new_qty = st.number_input(
                        t("pos.qty"),
                        min_value=0.0,
                        value=float(current["qty"]),
                        step=1.0,
                        key=f"edit_qty_{ticker}",
                    )
                    new_price = st.number_input(
                        t("pos.buy_price"),
                        min_value=0.0,
                        value=float(current["price"]),
                        step=1.0,
                        key=f"edit_price_{ticker}",
                    )
                    if "qty" not in pos:
                        st.caption(t("pos.cost_unknown"))
                    col_ok, col_del = st.columns(2)
                    if col_ok.button(t("side.save"), key=f"save_{ticker}", width="stretch"):
                        if new_qty > 0 and new_price > 0:
                            st.session_state.positions[ticker] = {
                                "qty": float(new_qty),
                                "price": float(new_price),
                            }
                        elif new_qty == 0:
                            st.session_state.positions.pop(ticker, None)
                        st.rerun()
                    if col_del.button(t("side.remove"), key=f"del_{ticker}", width="stretch"):
                        st.session_state.positions.pop(ticker, None)
                        st.rerun()
            st.caption(t("pos.total_cost", total=f"{total:,.0f}", n=len(positions)))
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
                        st.session_state.positions = normalize_portfolio(
                            parse_positions(uploaded.getvalue(), uploaded.name)
                        )
                        st.session_state.last_upload = file_id
                        st.toast(t("side.imported", n=len(st.session_state.positions)))
                        st.rerun()
                    except ValueError as exc:
                        st.error(t("side.import_failed", err=exc))

        saved = list_portfolios(advisor)
        with st.expander(t("side.saved_portfolios")):
            portfolio_name = st.text_input(t("side.name"), value="My portfolio")
            if st.button(t("side.save_composition"), width="stretch") and positions:
                save_portfolio(advisor, portfolio_name, positions)
                st.toast(t("side.saved_toast", name=portfolio_name))
            if saved:
                selected_saved = st.selectbox(
                    t("side.load"), sorted(saved), index=None,
                    placeholder=t("side.load_placeholder"),
                )
                if selected_saved and st.button(t("side.load_btn"), width="stretch"):
                    st.session_state.positions = normalize_portfolio(saved[selected_saved])
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
