"""Onboarding gate: landing → inserimento titoli → loading, poi la piattaforma.

Finché lo stage non è "app", la piattaforma è bloccata (sidebar nascosta).
"""

import random
import time

import streamlit as st

from src.i18n import t
from src.portfolio.positions import merge_lot
from src.ui.components import (
    eur,
    position_card_html,
    render_landing,
    sec,
    ticker_preview_html,
)
from src.views.common import (
    SAMPLE_PORTFOLIO,
    known_tickers,
    language_selector,
    ticker_preview,
)
from src.visualization.charts import PALETTE

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
    st.session_state.positions = {t_: dict(p) for t_, p in SAMPLE_PORTFOLIO.items()}


def _gate_add() -> None:
    chosen = st.session_state.get("gate_ticker")
    if not chosen:
        return
    k = str(chosen).upper().strip()
    qty = float(st.session_state.get(f"gate_qty_{k}") or 0)
    price = float(st.session_state.get(f"gate_price_{k}") or 0)
    if qty <= 0 or price <= 0:
        return
    st.session_state.positions[k] = merge_lot(st.session_state.positions.get(k), qty, price)
    st.session_state.gate_ticker = None


def render_gate() -> None:
    """Il flusso a tre stadi prima della piattaforma. Chiama st.stop() se attivo."""
    if "stage" not in st.session_state:
        st.session_state.stage = "landing"
    if st.session_state.stage == "app":
        return

    st.markdown(GATE_CSS, unsafe_allow_html=True)
    if st.session_state.stage != "loading":
        _spacer, lang_col = st.columns([6, 1])
        with lang_col:
            language_selector("lang_gate")

    # ---- stage 1: landing ------------------------------------------------
    if st.session_state.stage == "landing":
        render_landing(on_start=_go_input)

    # ---- stage 2: you must enter the tickers -----------------------------
    elif st.session_state.stage == "input":
        st.markdown(
            f"""
            <div class="gate-head">
              <div class="gate-step">{t("gate.step")}</div>
              <div class="gate-title">{t("gate.title")}</div>
              <div class="gate-sub">{t("gate.sub")}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        _l, mid, _r = st.columns([1, 2, 1])
        with mid:
            new_ticker = st.selectbox(
                "Search stock",
                known_tickers(),
                index=None,
                placeholder=t("gate.search_placeholder"),
                accept_new_options=True,
                label_visibility="collapsed",
                key="gate_ticker",
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
                col_qty, col_price, col_add = st.columns([2, 2, 2], gap="small")
                with col_qty:
                    st.number_input(
                        t("pos.qty"),
                        min_value=0.0001,
                        value=10.0,
                        step=1.0,
                        key=f"gate_qty_{key}",
                    )
                with col_price:
                    st.number_input(
                        t("pos.buy_price"),
                        min_value=0.0001,
                        value=default_price,
                        step=1.0,
                        key=f"gate_price_{key}",
                        help=t("pos.current_price") + f": {default_price:,.2f}",
                    )
                with col_add:
                    st.markdown("<div style='height:1.75rem'></div>", unsafe_allow_html=True)
                    st.button(
                        t("gate.add"), width="stretch", type="primary", on_click=_gate_add
                    )

            gate_positions = st.session_state.positions
            if gate_positions:
                sec(t("gate.your_holdings"))
                costs = {
                    ticker: (pos["qty"] * pos["price"] if "qty" in pos else pos.get("amount", 0.0))
                    for ticker, pos in gate_positions.items()
                }
                gate_total = sum(costs.values())
                for ticker in sorted(costs, key=costs.get, reverse=True):
                    pos = gate_positions[ticker]
                    color = PALETTE[sorted(costs).index(ticker) % len(PALETTE)]
                    weight = costs[ticker] / gate_total if gate_total else 0
                    company = st.session_state.get("names", {}).get(ticker, "")
                    label = (
                        f"{pos['qty']:g} × {pos['price']:,.2f}"
                        if "qty" in pos
                        else eur(pos.get("amount", 0.0))
                    )
                    col_card, col_del = st.columns([6, 1], gap="small")
                    with col_card:
                        st.markdown(
                            position_card_html(
                                ticker, costs[ticker], weight, color, company,
                                amount_label=label,
                            ),
                            unsafe_allow_html=True,
                        )
                    with col_del:
                        if st.button("✕", key=f"gate_del_{ticker}", width="stretch"):
                            st.session_state.positions.pop(ticker, None)
                            st.rerun()
                st.caption(t("pos.total_cost", total=f"{gate_total:,.0f}", n=len(gate_positions)))
            else:
                st.caption(t("gate.search_hint"))
                st.button(t("gate.sample"), on_click=_load_sample, width="stretch")

            st.divider()
            st.button(
                t("gate.analyze"),
                type="primary",
                width="stretch",
                on_click=_go_loading,
                disabled=not st.session_state.positions,
            )

    # ---- stage 3: gear + investing quote, then the platform opens --------
    elif st.session_state.stage == "loading":
        quote, author = random.choice(QUOTES)
        st.markdown(
            '<div class="loading-wrap">'
            + GEAR_SVG
            + f'<div class="loading-quote">“{quote}”</div>'
            + f'<div class="loading-author">— {author}</div>'
            + f'<div class="loading-hint">{t("gate.loading_hint")}</div>'
            + "</div>",
            unsafe_allow_html=True,
        )
        time.sleep(2.8)
        st.session_state.stage = "app"
        st.rerun()

    st.stop()
