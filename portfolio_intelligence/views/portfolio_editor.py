"""Editor delle posizioni condiviso: inserimento manuale, import da file, tabella.

Lavora sempre sul portafoglio di lavoro in `st.session_state.positions`. Lo
usano l'onboarding Investor (gate.py, prefisso "gate") e la scheda cliente
dell'area Advisor (prefisso "adv"): il prefisso separa le chiavi dei widget.
"""

from datetime import date

import streamlit as st

from portfolio_intelligence.data.importers import parse_positions
from portfolio_intelligence.i18n import t
from portfolio_intelligence.portfolio.positions import add_lot, aggregate, normalize_portfolio
from portfolio_intelligence.views.common import (
    cached_price_on,
    known_tickers,
    ticker_preview,
)

EDITOR_CSS = """
<style>
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
[class*="_pe_thead"], [class*="_pe_row_"] { border-bottom: 1px solid var(--line); }
[class*="_pe_thead"] [data-testid="stMarkdownContainer"],
[class*="_pe_row_"] [data-testid="stMarkdownContainer"] { margin-bottom: 0 !important; }
[class*="_pe_row_"] .stButton button { min-height: 28px; color: var(--muted); }
[class*="_pe_row_"] .stButton button:hover { color: var(--loss); }
.empty-tbl {
    border: 1px dashed var(--line-strong); border-radius: var(--r-lg);
    padding: var(--s-5); text-align: center; background: var(--panel);
}
.empty-tbl .t { font-weight: 600; color: var(--ink); font-size: 0.95rem; }
.empty-tbl .h { color: var(--muted); font-size: 0.88rem; margin-top: var(--s-1); }
</style>
"""


def inject_css() -> None:
    st.markdown(EDITOR_CSS, unsafe_allow_html=True)


def _remove_position(ticker: str) -> None:
    st.session_state.positions.pop(ticker, None)


def _clear_positions() -> None:
    st.session_state.positions = {}


def _add(prefix: str) -> None:
    chosen = st.session_state.get(f"{prefix}_ticker")
    if not chosen:
        return
    k = str(chosen).upper().strip()
    qty = float(st.session_state.get(f"{prefix}_qty_{k}") or 0)
    when = st.session_state.get(f"{prefix}_date_{k}")
    iso = when.isoformat() if when else ""
    price = float(st.session_state.get(f"{prefix}_price_{k}_{iso}") or 0)
    if price <= 0 and when:
        price = float(cached_price_on(k, iso) or 0)
    if qty <= 0 or price <= 0:
        st.toast(t("pos.price_lookup_failed", ticker=k, date=iso))
        return
    st.session_state.positions[k] = add_lot(st.session_state.positions.get(k), qty, price, when)
    st.session_state[f"{prefix}_ticker"] = None


def manual_entry(prefix: str) -> None:
    """Riga di inserimento: strumento, quantità, data, prezzo di carico, aggiungi."""
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
            key=f"{prefix}_ticker",
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
            key=f"{prefix}_qty_{key}",
            disabled=not key,
        )
    with c_date:
        buy_date = st.date_input(
            t("pos.buy_date"),
            value=date.today(),
            max_value=date.today(),
            key=f"{prefix}_date_{key}",
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
            key=f"{prefix}_price_{key}_{iso}",
            disabled=not key,
            help=t(
                "pos.price_auto_help",
                current=f"{current_price:,.2f}" if current_price else "—",
            ),
        )
    with c_add:
        st.button(
            t("gate.add_position"),
            key=f"{prefix}_add",
            type="primary",
            width="stretch",
            on_click=_add,
            args=(prefix,),
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


def file_import(prefix: str) -> None:
    """Import della posizione titoli del broker: sostituisce le posizioni correnti."""
    st.markdown(f'<div class="tab-desc">{t("gate.import_desc")}</div>', unsafe_allow_html=True)
    uploaded = st.file_uploader(
        t("side.upload_label"),
        type=["csv", "xlsx", "xls"],
        help=t("side.upload_help"),
        label_visibility="collapsed",
        key=f"{prefix}_upload",
    )
    if uploaded is None:
        return
    file_id = f"{prefix}-{uploaded.name}-{uploaded.size}"
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


def cost_basis(positions: dict) -> dict[str, tuple[float | None, float | None, float]]:
    """Per ticker: (quantità, prezzo medio di carico, controvalore di carico)."""
    rows: dict[str, tuple[float | None, float | None, float]] = {}
    for ticker, pos in positions.items():
        # formato storico {ticker: importo}: solo il controvalore, niente lotti
        pos = pos if isinstance(pos, dict) else {"amount": float(pos)}
        agg = aggregate(pos)
        if agg is not None:
            rows[ticker] = (agg["qty"], agg["price"], agg["qty"] * agg["price"])
        else:
            rows[ticker] = (None, None, float(pos.get("amount", 0.0)))
    return rows


def company_name(ticker: str) -> str:
    names = st.session_state.setdefault("names", {})
    if ticker not in names:
        preview = ticker_preview(ticker)
        names[ticker] = preview["name"] if preview else ""
    return names[ticker]


def positions_table(prefix: str, title: str | None = None, empty_hint: str | None = None) -> None:
    """Tabella delle posizioni con rimozione per riga e svuotamento."""
    positions = st.session_state.positions
    st.markdown(
        '<div class="tbl-title">'
        f'<span class="h">{title or t("gate.your_holdings")}</span>'
        f'<span class="n">{len(positions)}</span></div>',
        unsafe_allow_html=True,
    )
    if not positions:
        st.markdown(
            '<div class="empty-tbl">'
            f'<div class="t">{t("gate.empty_title")}</div>'
            f'<div class="h">{empty_hint or t("gate.empty_hint")}</div></div>',
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
    with st.container(key=f"{prefix}_pe_thead"):
        st.columns(widths, gap="small")[0].markdown(
            '<div class="tbl-grid head">'
            + "".join(f'<div class="th {css}">{label}</div>' for css, label in headers)
            + "</div>",
            unsafe_allow_html=True,
        )

    rows = cost_basis(positions)
    total = sum(cost for _, _, cost in rows.values())
    for ticker in sorted(rows, key=lambda k: rows[k][2], reverse=True):
        qty, avg, cost = rows[ticker]
        cells = [
            ("sym", ticker),
            ("name", company_name(ticker) or "—"),
            ("r", f"{qty:,.4g}" if qty is not None else "—"),
            ("r", f"{avg:,.2f}" if avg is not None else "—"),
            ("r", f"{cost:,.2f}"),
            ("r", f"{cost / total:.1%}" if total else "—"),
        ]
        with st.container(key=f"{prefix}_pe_row_{ticker}"):
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
                key=f"{prefix}_del_{ticker}",
                type="tertiary",
                on_click=_remove_position,
                args=(ticker,),
            )
    st.button(t("gate.clear"), key=f"{prefix}_clear", type="tertiary", on_click=_clear_positions)
