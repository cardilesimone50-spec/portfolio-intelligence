"""Onboarding gate: landing → composizione del portafoglio → loading, poi la piattaforma.

Finché lo stage non è "app", la piattaforma è bloccata (sidebar nascosta).
"""

from contextlib import suppress
from datetime import date

import streamlit as st

from portfolio_intelligence.data.importers import parse_positions
from portfolio_intelligence.i18n import t
from portfolio_intelligence.portfolio.positions import add_lot, aggregate, normalize_portfolio
from portfolio_intelligence.ui.components import render_landing
from portfolio_intelligence.ui.legal import legal_footer
from portfolio_intelligence.views.common import (
    BENCHMARK,
    SAMPLE_PORTFOLIO,
    analysis_fundamentals,
    cached_eurusd,
    cached_price_on,
    cached_prices,
    cached_risk_free,
    known_tickers,
    language_selector,
    ticker_preview,
)

# orizzonte di default della sidebar (pf_period): il caricamento scalda le
# stesse chiavi di cache che la piattaforma userà alla prima apertura
_DEFAULT_PERIOD = "1y"

GATE_CSS = """
<style>
/* while gated, nothing but the screen itself is reachable */
[data-testid="stSidebar"],
[data-testid="stSidebarCollapsedControl"],
[data-testid="collapsedControl"] { display: none !important; }

/* ---- header: brand + stepper ---- */
.gate-bar {
    display: flex; flex-wrap: wrap; align-items: center; gap: var(--s-2) var(--s-6);
    min-height: 40px;
}
.gate-bar .brand { white-space: nowrap; }
.stepper { display: flex; align-items: center; gap: var(--s-3); }
.step {
    display: flex; align-items: center; gap: var(--s-2);
    font-size: 0.85rem; font-weight: 600; color: var(--muted);
}
.step-num {
    width: 22px; height: 22px; border-radius: 50%;
    display: inline-flex; align-items: center; justify-content: center;
    font-size: 0.75rem; font-weight: 700;
    border: 1px solid var(--line-strong); background: var(--panel); color: var(--muted);
}
.step.active { color: var(--ink); }
.step.active .step-num { background: var(--ink); border-color: var(--ink); color: #fff; }
.step-sep { width: var(--s-6); height: 1px; background: var(--line-strong); }

.gate-head {
    margin: var(--s-4) 0 var(--s-5); padding-bottom: var(--s-5);
    border-bottom: 1px solid var(--line);
}
.gate-title {
    font-family: var(--font-display) !important; font-weight: 600;
    font-size: 1.75rem; letter-spacing: -0.01em; color: var(--ink); margin: 0; padding: 0;
}
.gate-sub {
    color: var(--muted); font-size: 0.95rem; margin-top: var(--s-2); max-width: 720px;
}

/* ---- riga sotto l'inserimento: nome, settore, prezzo ---- */
.instr-meta { font-size: 0.85rem; color: var(--muted); margin: 0 0 var(--s-1); }
.instr-meta b { color: var(--ink); font-weight: 600; }
.instr-meta .up { color: var(--gain); }
.instr-meta .down { color: var(--loss); }
.tab-desc {
    font-size: 0.9rem; color: var(--muted); line-height: 1.55; margin: 0 0 var(--s-3);
}

/* ---- tabella posizioni ---- */
.tbl-title { display: flex; gap: var(--s-2); align-items: baseline; margin: var(--s-6) 0 var(--s-2); }
.tbl-title .h { font-size: 1rem; font-weight: 700; color: var(--ink); }
.tbl-title .n {
    font-size: 0.75rem; font-weight: 600; color: var(--muted);
    background: var(--subtle); border-radius: var(--r-sm); padding: 1px var(--s-2);
}
.tbl-grid {
    display: grid; grid-template-columns: 0.9fr 2.3fr 0.9fr 1.5fr 1.5fr 0.8fr;
    gap: var(--s-3); align-items: center; min-height: 40px;
}
.tbl-grid.head { min-height: 28px; }
.th {
    font-size: 0.72rem; font-weight: 600; letter-spacing: 0.08em;
    text-transform: uppercase; color: var(--muted); white-space: nowrap;
}
.th.r, .td.r { text-align: right; }
.td { font-size: 0.9rem; color: var(--ink); font-variant-numeric: tabular-nums; }
.td.sym { font-weight: 700; letter-spacing: 0.02em; }
.td.name { color: var(--muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.st-key-gate_thead, [class*="st-key-gate_row_"] { border-bottom: 1px solid var(--line); }
.st-key-gate_thead [data-testid="stMarkdownContainer"],
[class*="st-key-gate_row_"] [data-testid="stMarkdownContainer"] { margin-bottom: 0 !important; }
[class*="st-key-gate_row_"] .stButton button { min-height: 28px; color: var(--muted); }
[class*="st-key-gate_row_"] .stButton button:hover { color: var(--loss); }
.empty-tbl {
    border: 1px dashed var(--line-strong); border-radius: var(--r-lg);
    padding: var(--s-5); text-align: center; background: var(--panel);
}
.empty-tbl .t { font-weight: 600; color: var(--ink); font-size: 0.95rem; }
.empty-tbl .h { color: var(--muted); font-size: 0.88rem; margin-top: var(--s-1); }

/* ---- riepilogo ---- */
.sum-h {
    font-size: 0.75rem; font-weight: 600; letter-spacing: 0.08em;
    text-transform: uppercase; color: var(--muted); margin-bottom: var(--s-1);
}
.sum-row {
    display: flex; justify-content: space-between; align-items: baseline; gap: var(--s-3);
    padding: var(--s-2) 0; border-bottom: 1px solid var(--line); font-size: 0.9rem;
}
.sum-row .k { color: var(--muted); }
.sum-row .v { color: var(--ink); font-weight: 600; font-variant-numeric: tabular-nums; }
.sum-note { font-size: 0.8rem; color: var(--muted); line-height: 1.5; }

/* ---- caricamento: overlay a schermo intero, nessun widget vecchio sotto ---- */
.loading-wrap {
    position: fixed; inset: 0; z-index: 99999; background: var(--bg);
    display: flex; align-items: center; justify-content: center; padding: var(--s-5);
}
.loading-card {
    width: 100%; max-width: 440px; background: var(--panel);
    border: 1px solid var(--line); border-radius: var(--r-lg);
    padding: var(--s-6) var(--s-6) var(--s-5);
}
.loading-card .brand { font-size: 0.85rem; margin-bottom: var(--s-5); }
.loading-title {
    font-family: var(--font-display) !important; font-weight: 600; font-size: 1.3rem;
    color: var(--ink);
}
.loading-sub { font-size: 0.88rem; color: var(--muted); margin-top: 2px; }
.loading-bar {
    height: 4px; background: var(--subtle); border-radius: 2px; margin: var(--s-4) 0 var(--s-2);
}
.loading-bar div { height: 100%; background: var(--accent); border-radius: 2px; }
/* l'indicatore "Running/Stop" di Streamlit non deve affiorare sopra la scheda */
body:has(.loading-wrap) [data-testid="stStatusWidget"] { visibility: hidden; }
.lstep {
    display: flex; align-items: center; gap: var(--s-3); padding: var(--s-2) 0;
    font-size: 0.9rem; color: var(--muted); border-top: 1px solid var(--line);
}
.loading-bar + .lstep { border-top: none; }
.lstep.done, .lstep.active { color: var(--ink); }
.lstep-ic {
    flex: none; width: 18px; height: 18px; border-radius: 50%;
    border: 1.5px solid var(--line-strong); display: inline-flex;
    align-items: center; justify-content: center;
}
.lstep.done .lstep-ic {
    background: var(--gain); border-color: var(--gain); color: #fff; font-size: 0.66rem;
}
/* unica animazione: indica il passo in corso, non decora */
.lstep.active .lstep-ic {
    border-color: var(--accent-border); border-top-color: var(--accent);
    animation: lspin .8s linear infinite;
}
@keyframes lspin { to { transform: rotate(360deg); } }
@media (prefers-reduced-motion: reduce) { .lstep.active .lstep-ic { animation: none; } }
</style>
"""


def _go_input() -> None:
    st.session_state.stage = "input"


def _go_loading() -> None:
    st.session_state.stage = "loading"


def _load_sample() -> None:
    st.session_state.positions = {t_: dict(p) for t_, p in SAMPLE_PORTFOLIO.items()}


def _clear_positions() -> None:
    st.session_state.positions = {}


def _remove_position(ticker: str) -> None:
    st.session_state.positions.pop(ticker, None)


def _gate_add() -> None:
    chosen = st.session_state.get("gate_ticker")
    if not chosen:
        return
    k = str(chosen).upper().strip()
    qty = float(st.session_state.get(f"gate_qty_{k}") or 0)
    when = st.session_state.get(f"gate_date_{k}")
    iso = when.isoformat() if when else ""
    price = float(st.session_state.get(f"gate_price_{k}_{iso}") or 0)
    if price <= 0 and when:
        price = float(cached_price_on(k, iso) or 0)
    if qty <= 0 or price <= 0:
        st.toast(t("pos.price_lookup_failed", ticker=k, date=iso))
        return
    st.session_state.positions[k] = add_lot(st.session_state.positions.get(k), qty, price, when)
    st.session_state.gate_ticker = None


def render_gate() -> None:
    """Il flusso a tre stadi prima della piattaforma. Chiama st.stop() se attivo."""
    if "stage" not in st.session_state:
        st.session_state.stage = "landing"
    if st.session_state.stage == "app":
        return

    st.markdown(GATE_CSS, unsafe_allow_html=True)

    # ---- stage 1: landing ------------------------------------------------
    if st.session_state.stage == "landing":
        _topbar(step=None)
        render_landing(on_start=_go_input)
        legal_footer()

    # ---- stage 2: portfolio composition ----------------------------------
    elif st.session_state.stage == "input":
        _topbar(step=1)
        _render_input()
        legal_footer()

    # ---- stage 3: real data fetch with progress, then the platform -------
    elif st.session_state.stage == "loading":
        _render_loading()

    st.stop()


def _topbar(step: int | None) -> None:
    """Marchio, avanzamento (solo nei passi del flusso) e lingua."""
    stepper = ""
    if step is not None:
        steps = [
            f'<div class="step{" active" if n == step else ""}">'
            f'<span class="step-num">{n}</span>{t(f"gate.step{n}")}</div>'
            for n in (1, 2)
        ]
        stepper = f'<div class="stepper">{steps[0]}<div class="step-sep"></div>{steps[1]}</div>'
    bar, lang_col = st.columns([6, 1], vertical_alignment="center")
    with bar:
        st.markdown(
            f'<div class="gate-bar"><div class="brand">◆ SMARTEE<b>FINANCE</b></div>{stepper}</div>',
            unsafe_allow_html=True,
        )
    with lang_col:
        language_selector("lang_gate")


# ----------------------------------------------------------------- stage 2


def _render_input() -> None:
    st.markdown(
        '<div class="gate-head">'
        f'<h1 class="page-title gate-title">{t("gate.title")}</h1>'
        f'<div class="gate-sub">{t("gate.sub")}</div>'
        "</div>",
        unsafe_allow_html=True,
    )

    main, side = st.columns([2.4, 1], gap="large")
    with main:
        with st.container(border=True):
            tab_manual, tab_import, tab_sample = st.tabs(
                [t("gate.tab_manual"), t("gate.tab_import"), t("gate.tab_sample")]
            )
            with tab_manual:
                _manual_entry()
            with tab_import:
                _file_import()
            with tab_sample:
                st.markdown(
                    f'<div class="tab-desc">{t("gate.sample_desc")}</div>',
                    unsafe_allow_html=True,
                )
                st.button(t("gate.sample"), on_click=_load_sample)
        _positions_table()
    with side:
        _summary_panel()


def _manual_entry() -> None:
    c_sym, c_qty, c_date, c_price, c_add = st.columns(
        [2.1, 1.0, 1.3, 1.5, 1.2], gap="small", vertical_alignment="bottom"
    )
    with c_sym:
        chosen = st.selectbox(
            t("gate.instrument"),
            known_tickers(),
            index=None,
            placeholder=t("gate.search_placeholder"),
            accept_new_options=True,
            key="gate_ticker",
        )
    key = str(chosen).upper().strip() if chosen else ""
    preview = ticker_preview(key) if key else None
    current_price = float(preview["price"]) if preview and preview.get("price") else None
    with c_qty:
        st.number_input(
            t("pos.qty"),
            min_value=0.0001,
            value=10.0,
            step=1.0,
            key=f"gate_qty_{key}",
            disabled=not key,
        )
    with c_date:
        buy_date = st.date_input(
            t("pos.buy_date"),
            value=date.today(),
            max_value=date.today(),
            key=f"gate_date_{key}",
            disabled=not key,
        )
    # il prezzo si ricava dalla data: chiusura storica dal database,
    # con l'ultimo prezzo come ripiego; resta modificabile a mano
    iso = buy_date.isoformat() if buy_date else ""
    looked_up = cached_price_on(key, iso) if key and iso else None
    default_price = looked_up or current_price or (100.0 if key else 0.0)
    with c_price:
        st.number_input(
            t("pos.buy_price"),
            min_value=0.0,
            value=float(default_price),
            step=1.0,
            format="%.2f",
            key=f"gate_price_{key}_{iso}",
            disabled=not key,
            help=t(
                "pos.price_auto_help",
                current=f"{current_price:,.2f}" if current_price else "—",
            ),
        )
    with c_add:
        st.button(
            t("gate.add_position"),
            type="primary",
            width="stretch",
            on_click=_gate_add,
            disabled=not key,
        )

    if not key:
        return
    if preview:
        st.session_state.setdefault("names", {})[key] = preview["name"]
        parts = [f"<b>{preview['name']}</b>"]
        if preview.get("sector"):
            parts.append(preview["sector"])
        if current_price is not None:
            sym = "$" if preview.get("currency") == "USD" else preview.get("currency", "")
            price = f"{sym}{current_price:,.2f}"
            chg = preview.get("change")
            if chg is not None:
                css = "up" if chg >= 0 else "down"
                price += f' <span class="{css}">{chg:+.2f}%</span>'
            parts.append(price)
        meta = " · ".join(parts)
    else:
        meta = f"<b>{key}</b>"
    st.markdown(f'<div class="instr-meta">{meta}</div>', unsafe_allow_html=True)


def _file_import() -> None:
    st.markdown(f'<div class="tab-desc">{t("gate.import_desc")}</div>', unsafe_allow_html=True)
    uploaded = st.file_uploader(
        t("side.upload_label"),
        type=["csv", "xlsx", "xls"],
        help=t("side.upload_help"),
        label_visibility="collapsed",
        key="gate_upload",
    )
    if uploaded is None:
        return
    file_id = f"{uploaded.name}-{uploaded.size}"
    if st.session_state.get("last_upload") == file_id:
        return
    try:
        st.session_state.positions = normalize_portfolio(
            parse_positions(uploaded.getvalue(), uploaded.name)
        )
    except ValueError as exc:
        st.error(t("side.import_failed", err=exc))
        return
    st.session_state.last_upload = file_id
    st.toast(t("side.imported", n=len(st.session_state.positions)))
    st.rerun()


def _cost_basis(positions: dict) -> dict[str, tuple[float | None, float | None, float]]:
    """Per ticker: (quantità, prezzo medio di carico, controvalore di carico)."""
    rows: dict[str, tuple[float | None, float | None, float]] = {}
    for ticker, pos in positions.items():
        agg = aggregate(pos)
        if agg is not None:
            rows[ticker] = (agg["qty"], agg["price"], agg["qty"] * agg["price"])
        else:
            rows[ticker] = (None, None, float(pos.get("amount", 0.0)))
    return rows


def _company_name(ticker: str) -> str:
    names = st.session_state.setdefault("names", {})
    if ticker not in names:
        preview = ticker_preview(ticker)
        names[ticker] = preview["name"] if preview else ""
    return names[ticker]


def _positions_table() -> None:
    positions = st.session_state.positions
    st.markdown(
        '<div class="tbl-title">'
        f'<span class="h">{t("gate.your_holdings")}</span>'
        f'<span class="n">{len(positions)}</span></div>',
        unsafe_allow_html=True,
    )
    if not positions:
        st.markdown(
            '<div class="empty-tbl">'
            f'<div class="t">{t("gate.empty_title")}</div>'
            f'<div class="h">{t("gate.empty_hint")}</div></div>',
            unsafe_allow_html=True,
        )
        return

    headers = [
        ("", t("gate.col_instrument")),
        ("", ""),
        ("r", t("pos.qty")),
        ("r", t("gate.col_avg_price")),
        ("r", t("gate.col_cost")),
        ("r", t("gate.col_weight")),
    ]
    widths = [12, 1.6]  # griglia dati | azione di rimozione
    with st.container(key="gate_thead"):
        st.columns(widths, gap="small")[0].markdown(
            '<div class="tbl-grid head">'
            + "".join(f'<div class="th {css}">{label}</div>' for css, label in headers)
            + "</div>",
            unsafe_allow_html=True,
        )

    rows = _cost_basis(positions)
    total = sum(cost for _, _, cost in rows.values())
    for ticker in sorted(rows, key=lambda k: rows[k][2], reverse=True):
        qty, avg, cost = rows[ticker]
        cells = [
            ("sym", ticker),
            ("name", _company_name(ticker) or "—"),
            ("r", f"{qty:,.4g}" if qty is not None else "—"),
            ("r", f"{avg:,.2f}" if avg is not None else "—"),
            ("r", f"{cost:,.2f}"),
            ("r", f"{cost / total:.1%}" if total else "—"),
        ]
        with st.container(key=f"gate_row_{ticker}"):
            data_col, action_col = st.columns(widths, gap="small", vertical_alignment="center")
            data_col.markdown(
                '<div class="tbl-grid">'
                + "".join(f'<div class="td {css}">{text}</div>' for css, text in cells)
                + "</div>",
                unsafe_allow_html=True,
            )
            # etichetta testuale, non "✕": è il nome letto dai lettori di schermo
            action_col.button(
                t("side.remove"),
                key=f"gate_del_{ticker}",
                type="tertiary",
                on_click=_remove_position,
                args=(ticker,),
            )
    st.button(t("gate.clear"), type="tertiary", on_click=_clear_positions)


def _summary_panel() -> None:
    positions = st.session_state.positions
    rows = _cost_basis(positions)
    costs = sorted((cost for _, _, cost in rows.values()), reverse=True)
    total = sum(costs)
    if total:
        largest = max(rows, key=lambda k: rows[k][2])
        largest_txt = f"{largest} · {rows[largest][2] / total:.1%}"
        top3_txt = f"{sum(costs[:3]) / total:.1%}"
        total_txt = f"{total:,.2f}"
    else:
        largest_txt = top3_txt = total_txt = "—"

    summary = [
        (t("gate.sum_positions"), str(len(positions))),
        (t("gate.sum_invested"), total_txt),
        (t("gate.sum_largest"), largest_txt),
        (t("gate.sum_top3"), top3_txt),
    ]
    with st.container(border=True):
        st.markdown(
            f'<div class="sum-h">{t("gate.summary")}</div>'
            + "".join(
                f'<div class="sum-row"><span class="k">{k}</span><span class="v">{v}</span></div>'
                for k, v in summary
            ),
            unsafe_allow_html=True,
        )
        st.button(
            t("gate.analyze"),
            type="primary",
            width="stretch",
            on_click=_go_loading,
            disabled=not positions,
            help=None if positions else t("gate.analyze_disabled"),
        )
        st.markdown(
            f'<div class="sum-note">{t("gate.analyze_note")}</div>',
            unsafe_allow_html=True,
        )


# ----------------------------------------------------------------- stage 3


def _loading_html(labels: list[str], done: int, n_positions: int) -> str:
    rows = ""
    for i, label in enumerate(labels):
        state = "done" if i < done else "active" if i == done else ""
        icon = "✓" if i < done else ""
        rows += f'<div class="lstep {state}"><span class="lstep-ic">{icon}</span>{label}</div>'
    pct = done / len(labels) * 100
    return (
        '<div class="loading-wrap"><div class="loading-card">'
        '<div class="brand">◆ SMARTEE<b>FINANCE</b></div>'
        f'<div class="loading-title">{t("gate.loading_title")}</div>'
        f'<div class="loading-sub">{t("gate.loading_sub", n=n_positions)}</div>'
        f'<div class="loading-bar"><div style="width:{pct:.0f}%"></div></div>'
        f"{rows}</div></div>"
    )


def _render_loading() -> None:
    """Scarica davvero i dati dell'analisi, mostrando l'avanzamento passo per passo.

    Scalda le cache che la piattaforma interroga alla prima apertura, così la
    vista si apre già pronta invece di mostrare spinner in sequenza.
    """
    tickers = tuple(sorted(st.session_state.positions))
    tasks = [
        (
            t("gate.load_prices"),
            lambda: (
                cached_prices(tickers, _DEFAULT_PERIOD),
                cached_prices((BENCHMARK,), _DEFAULT_PERIOD),
            ),
        ),
        (t("gate.load_fx"), lambda: cached_eurusd(_DEFAULT_PERIOD)),
        (t("gate.load_fundamentals"), lambda: analysis_fundamentals(tickers)),
        (t("gate.load_rates"), cached_risk_free),
    ]
    labels = [label for label, _ in tasks]
    placeholder = st.empty()
    for i, (_label, task) in enumerate(tasks):
        placeholder.markdown(_loading_html(labels, i, len(tickers)), unsafe_allow_html=True)
        # nessun blocco qui: la piattaforma rifà la chiamata e mostra
        # l'errore nel suo contesto, con il messaggio giusto
        with suppress(Exception):
            task()
    placeholder.markdown(_loading_html(labels, len(tasks), len(tickers)), unsafe_allow_html=True)
    st.session_state.stage = "app"
    st.rerun()
