"""Spazio di lavoro dell'area Advisor: un'interfaccia da consulente, non da investitore.

Struttura (diversa da Investor, che è un percorso guidato per un solo portafoglio):
- navigazione a sinistra: Clienti, Nuovo cliente, il cliente attivo con le sue
  sezioni, Mercato, Amministrazione; in basso parametri, privacy e lingua;
- Clienti (pagina iniziale): il book con indicatori sintetici e una riga per
  cliente, ordinato da chi richiede attenzione per primo;
- Nuovo cliente: codice, profilo di rischio dichiarato e posizioni;
- scheda cliente: intestazione con profilo e stato, sezioni Panoramica,
  Posizioni, Analisi, Strategie. Le viste di analisi sono le stesse di
  Investor, ma lavorano sul cliente e salvano su DB, isolate per consulente.

Stato di sessione: `adv_page`, `adv_client` (codice del cliente attivo),
`adv_saved` (le posizioni salvate, per riconoscere le modifiche) e
`positions` (il portafoglio di lavoro, condiviso con le viste).
"""

import json
from collections.abc import Callable

import streamlit as st

from portfolio_intelligence.config import HEALTH_SCORE_FAIR
from portfolio_intelligence.data.store import (
    REDACTED,
    delete_advisor_data,
    delete_portfolio,
    list_clients,
    log_audit,
    save_portfolio,
)
from portfolio_intelligence.i18n import t
from portfolio_intelligence.portfolio.positions import normalize_portfolio
from portfolio_intelligence.router import compute_portfolio
from portfolio_intelligence.ui.components import compliance_footer, eur, sec, text_safe
from portfolio_intelligence.ui.identity import auth_configured, is_admin, is_authenticated
from portfolio_intelligence.ui.legal import legal_footer
from portfolio_intelligence.views import (
    admin,
    backtest,
    checkup,
    correlations,
    fundamentals,
    market,
    metrics,
    optimize,
    options_overlay,
    visual,
)
from portfolio_intelligence.views import portfolio_editor as pe
from portfolio_intelligence.views.clients import quick_client_analysis, status_color
from portfolio_intelligence.views.common import PROFILE_VOL, SAMPLE_PORTFOLIO, language_selector
from portfolio_intelligence.views.context import ViewContext
from portfolio_intelligence.views.sidebar import (
    RISK_PROFILES,
    SidebarSettings,
    analysis_parameters,
)

DEMO_CLIENT = "DEMO-001"

WORKSPACE_CSS = """
<style>
/* ---- navigazione a sinistra ---- */
.adv-brand { font-size: 0.9rem; margin: 0 0 var(--s-2); line-height: 1.6; }
.adv-brand .brand-product { margin-left: var(--s-2); padding-left: var(--s-2); }
.adv-identity {
    font-size: 0.8rem; color: var(--muted); margin-bottom: var(--s-4);
    overflow-wrap: anywhere; line-height: 1.4;
}
.adv-rail-label {
    font-size: 0.7rem; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase;
    color: var(--muted); margin: var(--s-4) 0 var(--s-1); padding-left: var(--s-3);
}
[class*="st-key-advnav_"] button {
    justify-content: flex-start; width: 100%; border: none; background: transparent;
    color: var(--ink-2); padding: var(--s-1) var(--s-3); min-height: 34px;
    border-radius: var(--r-md);
}
[class*="st-key-advnav_"] button div { justify-content: flex-start; }
[class*="st-key-advnav_"] button p { font-weight: 600; font-size: 0.92rem; }
[class*="st-key-advnav_"] button:hover { background: var(--subtle); color: var(--ink); }
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: 2px; }
[data-testid="stSidebar"] [data-testid="stExpander"] { margin-top: var(--s-2); }
.adv-rail-foot { font-size: 0.8rem; margin-top: var(--s-4); }
.adv-rail-foot a { color: var(--muted); text-decoration: underline; }

/* ---- intestazione di pagina ---- */
.adv-head { padding: var(--s-2) 0 var(--s-4); border-bottom: 1px solid var(--line);
            margin-bottom: var(--s-5); }
.adv-crumb { font-size: 0.8rem; color: var(--muted); margin-bottom: var(--s-2); }
.adv-title {
    font-family: var(--font-display) !important; font-weight: 600; font-size: 1.9rem;
    letter-spacing: -0.01em; color: var(--ink);
}
.adv-meta { color: var(--muted); font-size: 0.92rem; margin-top: var(--s-2); }
.adv-dirty { color: var(--ink-2); font-size: 0.85rem; margin-top: var(--s-2); }

/* ---- sezioni del cliente (sotto-navigazione a schede) ---- */
.st-key-adv_section { border-bottom: 1px solid var(--line); margin-bottom: var(--s-4); }
.st-key-adv_section [role="radiogroup"] button,
.st-key-adv_sub [role="radiogroup"] button {
    background: transparent !important; border: none !important; border-radius: 0 !important;
    border-bottom: 2px solid transparent !important; padding: var(--s-2) var(--s-4) !important;
}
.st-key-adv_section button p { font-weight: 600; font-size: 0.92rem; color: var(--muted) !important; }
.st-key-adv_section button[aria-checked="true"],
.st-key-adv_section button[kind="segmented_controlActive"] {
    border-bottom-color: var(--accent) !important;
}
.st-key-adv_section button[aria-checked="true"] p,
.st-key-adv_section button[kind="segmented_controlActive"] p { color: var(--ink) !important; }
.st-key-adv_sub button p { font-size: 0.85rem; color: var(--muted) !important; }
.st-key-adv_sub button[aria-checked="true"] p,
.st-key-adv_sub button[kind="segmented_controlActive"] p { color: var(--ink) !important; font-weight: 600; }

/* ---- book clienti ---- */
.book-grid {
    display: grid; grid-template-columns: 1.4fr 1fr 1.1fr 0.9fr 0.9fr 0.7fr 3fr;
    gap: var(--s-3); align-items: center; min-height: 48px;
}
.book-grid.head { min-height: 30px; }
.book-grid .th {
    font-size: 0.72rem; font-weight: 600; letter-spacing: 0.08em;
    text-transform: uppercase; color: var(--muted); white-space: nowrap;
}
.book-grid .th.num { text-align: right; }
.book-grid .c-code { font-weight: 700; color: var(--ink); }
.book-grid .num { text-align: right; font-variant-numeric: tabular-nums; }
.book-grid .health { font-weight: 700; text-align: right; font-variant-numeric: tabular-nums; }
.book-grid .flag { color: var(--ink-2); font-size: 0.86rem; line-height: 1.4; }
.book-grid .dot {
    display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: var(--s-2);
}
.st-key-adv_book_head, [class*="st-key-adv_book_row_"] { border-bottom: 1px solid var(--line); }
.st-key-adv_book_head [data-testid="stMarkdownContainer"],
[class*="st-key-adv_book_row_"] [data-testid="stMarkdownContainer"] { margin-bottom: 0 !important; }
.book-wrap {
    background: var(--panel); border: 1px solid var(--line); border-radius: var(--r-lg);
    padding: var(--s-2) var(--s-4);
}

/* ---- riepilogo nuovo cliente ---- */
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
</style>
"""


# ------------------------------------------------------------------ stato


def _goto(page: str) -> None:
    st.session_state.adv_page = page


def _new_client() -> None:
    st.session_state.adv_page = "new_client"
    st.session_state.adv_client = None
    st.session_state.positions = {}


def _open_client(name: str, positions: dict, section: str = "overview") -> None:
    st.session_state.adv_page = "client"
    st.session_state.adv_client = name
    st.session_state.adv_section = section
    st.session_state.positions = normalize_portfolio(positions)
    st.session_state.adv_saved = _fingerprint(st.session_state.positions)


def _fingerprint(positions: dict) -> str:
    return json.dumps(positions, sort_keys=True, default=str)


def _goto_section(section: str) -> None:
    st.session_state.adv_page = "client"
    st.session_state.adv_section = section


# ------------------------------------------------------------------ navigazione


def _nav_button(key: str, label: str, on_click: Callable, args: tuple = ()) -> None:
    st.button(
        label, key=f"advnav_{key}", type="tertiary", width="stretch", on_click=on_click, args=args
    )


def _render_rail(advisor: str, clients: dict) -> tuple[str, bool, float]:
    page = st.session_state.adv_page
    client = st.session_state.get("adv_client")
    section = st.session_state.get("adv_section", "overview")
    active_key = {
        "clients": "clients",
        "new_client": "new",
        "market": "market",
        "admin": "admin",
    }.get(page, "client")
    # voce attiva evidenziata: sfondo tenue e testo pieno, nessun colore decorativo
    st.markdown(
        f"<style>.st-key-advnav_{active_key} button {{ background: var(--accent-soft) !important; }}"
        f".st-key-advnav_{active_key} button p {{ color: var(--accent) !important; }}</style>",
        unsafe_allow_html=True,
    )
    with st.sidebar:
        st.markdown(
            '<div class="brand adv-brand">◆ SMARTEE<b>FINANCE</b>'
            f'<span class="brand-product">{t("adv.product")}</span></div>',
            unsafe_allow_html=True,
        )
        if auth_configured() and is_authenticated():
            st.markdown(
                f'<div class="adv-identity">{t("adv.signed_in", advisor=advisor)}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="adv-identity">{t("adv.dev_env")}</div>', unsafe_allow_html=True
            )

        _nav_button("clients", t("adv.nav_clients"), _goto, ("clients",))
        _nav_button("new", t("adv.nav_new"), _new_client)
        if client and client in clients:
            st.markdown(
                f'<div class="adv-rail-label">{t("adv.nav_active")}</div>',
                unsafe_allow_html=True,
            )
            _nav_button("client", client, _goto_section, (section,))
        st.markdown('<div class="adv-rail-label"></div>', unsafe_allow_html=True)
        _nav_button("market", t("adv.nav_market"), _goto, ("market",))
        if is_admin(advisor):
            _nav_button("admin", t("adv.nav_admin"), _goto, ("admin",))

        with st.expander(t("adv.params")):
            period, in_eur, risk_free = analysis_parameters("adv")
        with st.expander(t("side.privacy")):
            st.caption(t("side.erase_all_hint"))
            confirm_all = st.checkbox(t("side.erase_all_confirm"), key="erase_all_confirm")
            if st.button(t("side.erase_all_btn"), width="stretch", disabled=not confirm_all):
                counts = delete_advisor_data(advisor)
                st.session_state.positions = {}
                st.session_state.adv_client = None
                st.session_state.adv_page = "clients"
                st.toast(t("side.erase_all_done", **counts))
                st.rerun()
        language_selector("lang_adv")
        if (
            auth_configured()
            and is_authenticated()
            and st.button(t("side.logout"), key="adv_logout", width="stretch")
        ):
            st.logout()
        st.markdown(
            f'<div class="adv-rail-foot"><a href="?profile=investor" target="_self">'
            f"{t('adv.switch_area')}</a></div>",
            unsafe_allow_html=True,
        )
    return period, in_eur, risk_free


def _page_header(title: str, crumb: str | None = None, meta: str | None = None) -> None:
    st.markdown(
        '<div class="adv-head">'
        + (f'<div class="adv-crumb">{crumb}</div>' if crumb else "")
        + f'<h1 class="page-title adv-title">{title}</h1>'
        + (f'<div class="adv-meta">{meta}</div>' if meta else "")
        + "</div>",
        unsafe_allow_html=True,
    )


def _context(
    advisor: str,
    name: str,
    profile: str,
    period: str,
    in_eur: bool,
    risk_free: float,
) -> tuple[ViewContext, str | None, str | None]:
    positions = normalize_portfolio(st.session_state.positions)
    settings = SidebarSettings(name, period, in_eur, risk_free, profile)
    cp = compute_portfolio(positions, settings)
    ctx = ViewContext(
        computed=cp.computed,
        amounts=cp.amounts,
        total=cp.total,
        portfolio=cp.portfolio,
        portfolio_name=name,
        period=period,
        in_eur=in_eur,
        risk_free=risk_free,
        risk_profile=profile,
        advisor=advisor,
        names=cp.names,
        pos=cp.pos_table,
        pnl_totals=cp.pnl_totals,
        irr=cp.irr,
        stateful=True,
    )
    return ctx, cp.compute_error, cp.notice


# ------------------------------------------------------------------ pagine


def _book_rows(clients: dict, period: str, in_eur: bool) -> list[dict]:
    rows = []
    for name, record in clients.items():
        row = {"name": name, "profile": record["risk_profile"], "positions": record["positions"]}
        try:
            row.update(
                quick_client_analysis(
                    tuple(sorted(record["positions"].items())),
                    period,
                    in_eur,
                    st.session_state.get("language", "en"),
                )
            )
        except (ValueError, KeyError, ZeroDivisionError) as exc:
            row["error"] = str(exc)
        band = PROFILE_VOL.get(record["risk_profile"])
        row["review"] = "error" not in row and (
            row["health"] < HEALTH_SCORE_FAIR or (band is not None and row["vol"] > band)
        )
        rows.append(row)
    # chi richiede attenzione per primo: da rivedere, poi Health crescente
    return sorted(rows, key=lambda r: (not r["review"], r.get("health", 101), r["name"]))


def _create_demo(advisor: str) -> None:
    save_portfolio(advisor, DEMO_CLIENT, SAMPLE_PORTFOLIO, risk_profile="Moderate")
    log_audit(advisor, "create_client", DEMO_CLIENT)
    _open_client(DEMO_CLIENT, SAMPLE_PORTFOLIO)


def _page_clients(advisor: str, clients: dict, period: str, in_eur: bool) -> None:
    _page_header(t("adv.clients_title"), meta=t("adv.clients_sub"))
    if not clients:
        st.markdown(
            f'<div class="empty"><div class="empty-title">{t("adv.no_clients_title")}</div>'
            f'<div class="empty-hint">{t("adv.no_clients_hint")}</div></div>',
            unsafe_allow_html=True,
        )
        left, right, _rest = st.columns([1, 1, 2])
        left.button(t("adv.nav_new"), type="primary", width="stretch", on_click=_new_client)
        right.button(t("adv.demo_client"), width="stretch", on_click=_create_demo, args=(advisor,))
        return

    with st.spinner(t("app.loading_data")):
        rows = _book_rows(clients, period, in_eur)
    analysed = [r for r in rows if "error" not in r]
    aum = sum(r["value"] for r in analysed)
    avg_health = round(sum(r["health"] for r in analysed) / len(analysed)) if analysed else None
    cells = [
        (t("adv.kpi_clients"), str(len(rows)), t("adv.kpi_clients_sub")),
        (t("adv.kpi_aum"), eur(aum) if analysed else "—", t("adv.kpi_aum_sub")),
        (
            t("adv.kpi_review"),
            str(sum(r["review"] for r in rows)),
            t("adv.kpi_review_sub", fair=HEALTH_SCORE_FAIR),
        ),
        (
            t("adv.kpi_health"),
            str(avg_health) if avg_health is not None else "—",
            t("adv.kpi_health_sub"),
        ),
    ]
    st.markdown(
        '<div class="kpi-row">'
        + "".join(
            f'<div class="kpi"><div class="kpi-label">{label}</div>'
            f'<div class="kpi-value">{value}</div><div class="kpi-sub">{sub}</div></div>'
            for label, value, sub in cells
        )
        + "</div>",
        unsafe_allow_html=True,
    )

    search_col, _gap, new_col = st.columns([2, 1.6, 1], vertical_alignment="bottom")
    query = search_col.text_input(
        t("adv.search"),
        key="adv_search",
        placeholder=t("adv.search"),
        label_visibility="collapsed",
    )
    new_col.button(t("adv.nav_new"), type="primary", width="stretch", on_click=_new_client)
    shown = [r for r in rows if query.strip().lower() in r["name"].lower()]
    if not shown:
        st.caption(t("adv.no_match"))
        return

    headers = [
        ("", t("adv.col_client")),
        ("", t("adv.col_profile")),
        ("num", t("adv.col_value")),
        ("num", t("adv.col_return")),
        ("num", t("adv.col_vol")),
        ("num", t("adv.col_health")),
        ("", t("adv.col_flag")),
    ]
    widths = [12, 1.3]
    with st.container(key="adv_book_head"):
        st.columns(widths, gap="small")[0].markdown(
            '<div class="book-grid head">'
            + "".join(f'<div class="th {css}">{label}</div>' for css, label in headers)
            + "</div>",
            unsafe_allow_html=True,
        )
    for i, row in enumerate(shown):
        if "error" in row:
            data = [
                ("c-code", row["name"]),
                ("", t(f"prof.{row['profile']}")),
                ("num", "—"),
                ("num", "—"),
                ("num", "—"),
                ("health", "—"),
                ("flag", t("adv.analysis_failed", err=row["error"])),
            ]
        else:
            color = status_color(row["health"])
            ret = row["pnl_pct"] if row["pnl_pct"] == row["pnl_pct"] else row["cum"]
            data = [
                ("c-code", f'<span class="dot" style="background:{color}"></span>{row["name"]}'),
                ("", t(f"prof.{row['profile']}")),
                ("num", eur(row["value"])),
                ("num " + ("up" if ret >= 0 else "down"), f"{ret:+.1%}"),
                ("num", f"{row['vol']:.1%}"),
                ("health", f'<span style="color:{text_safe(color)}">{row["health"]}</span>'),
                ("flag", row["problem"]),
            ]
        with st.container(key=f"adv_book_row_{i}"):
            cell_col, action_col = st.columns(widths, gap="small", vertical_alignment="center")
            cell_col.markdown(
                '<div class="book-grid">'
                + "".join(f'<div class="{css}">{text}</div>' for css, text in data)
                + "</div>",
                unsafe_allow_html=True,
            )
            action_col.button(
                t("adv.open"),
                key=f"adv_open_{i}",
                width="stretch",
                on_click=_open_client,
                args=(row["name"], row["positions"]),
            )


def _create_client(advisor: str, existing: dict) -> None:
    name = (st.session_state.get("adv_new_name") or "").strip()
    profile = st.session_state.get("adv_new_profile", "Not set")
    positions = st.session_state.positions
    if not name or not positions or name in existing:
        return
    save_portfolio(advisor, name, positions, risk_profile=profile)
    log_audit(advisor, "create_client", name)
    st.session_state.adv_new_name = ""
    _open_client(name, positions)
    st.toast(t("adv.created", name=name))


def _page_new_client(advisor: str, clients: dict) -> None:
    pe.inject_css()
    _page_header(t("adv.new_title"), crumb=t("adv.nav_clients"), meta=t("adv.new_sub"))
    main, side = st.columns([2.4, 1], gap="large")
    with main:
        with st.container(border=True):
            sec(t("adv.registry"))
            code_col, profile_col = st.columns([1.4, 1])
            code_col.text_input(
                t("adv.client_code"), key="adv_new_name", help=t("adv.client_code_help")
            )
            profile_col.selectbox(
                t("side.risk_profile"),
                RISK_PROFILES,
                key="adv_new_profile",
                format_func=lambda p: t(f"prof.{p}"),
            )
            name = (st.session_state.get("adv_new_name") or "").strip()
            if name in clients:
                st.error(t("adv.code_exists"))
        with st.container(border=True):
            tab_manual, tab_import = st.tabs([t("gate.tab_manual"), t("gate.tab_import")])
            with tab_manual:
                pe.manual_entry("adv")
            with tab_import:
                pe.file_import("adv")
        pe.positions_table("adv", empty_hint=t("adv.empty_positions"))
    with side, st.container(border=True):
        positions = st.session_state.positions
        invested = sum(cost for _, _, cost in pe.cost_basis(positions).values())
        profile = st.session_state.get("adv_new_profile", "Not set")
        rows = [
            (t("adv.client_code"), name or "—"),
            (t("side.risk_profile"), t(f"prof.{profile}")),
            (t("gate.sum_positions"), str(len(positions))),
            (t("gate.sum_invested"), f"{invested:,.2f}" if invested else "—"),
        ]
        st.markdown(
            f'<div class="sum-h">{t("gate.summary")}</div>'
            + "".join(
                f'<div class="sum-row"><span class="k">{k}</span><span class="v">{v}</span></div>'
                for k, v in rows
            ),
            unsafe_allow_html=True,
        )
        ready = bool(name) and bool(positions) and name not in clients
        st.button(
            t("adv.create"),
            type="primary",
            width="stretch",
            disabled=not ready,
            help=None if ready else t("adv.create_disabled"),
            on_click=_create_client,
            args=(advisor, clients),
        )


def _save_positions(advisor: str, name: str) -> None:
    save_portfolio(advisor, name, st.session_state.positions)
    log_audit(advisor, "save_portfolio", name)
    st.session_state.adv_saved = _fingerprint(st.session_state.positions)
    st.toast(t("adv.saved"))


def _save_profile(advisor: str, name: str) -> None:
    profile = st.session_state.get("adv_profile_edit", "Not set")
    save_portfolio(
        advisor,
        name,
        normalize_portfolio(st.session_state.adv_saved_positions),
        risk_profile=profile,
    )
    log_audit(advisor, "update_profile", name)
    st.toast(t("adv.profile_saved"))


def _delete_client(advisor: str, name: str) -> None:
    delete_portfolio(advisor, name)
    log_audit(advisor, "delete_portfolio", REDACTED)
    st.session_state.adv_client = None
    st.session_state.adv_page = "clients"
    st.session_state.positions = {}
    st.toast(t("side.deleted_toast"))


def _page_client(advisor: str, clients: dict, period: str, in_eur: bool, risk_free: float) -> None:
    name = st.session_state.adv_client
    record = clients[name]
    profile = record["risk_profile"]
    dirty = _fingerprint(st.session_state.positions) != st.session_state.get("adv_saved")
    st.session_state.adv_saved_positions = record["positions"]

    head_col, action_col = st.columns([4, 1], vertical_alignment="bottom")
    with head_col:
        _page_header(
            name,
            crumb=t("adv.nav_clients"),
            meta=t(
                "adv.meta",
                profile=t(f"prof.{profile}"),
                n=len(st.session_state.positions),
                updated=str(record["updated"])[:10],
            ),
        )
    with action_col:
        st.button(
            t("adv.save"),
            type="primary",
            width="stretch",
            disabled=not dirty,
            on_click=_save_positions,
            args=(advisor, name),
        )
    if dirty:
        st.markdown(f'<div class="adv-dirty">{t("adv.unsaved")}</div>', unsafe_allow_html=True)

    sections = ["overview", "positions", "analysis", "strategies"]
    current = st.session_state.get("adv_section", "overview")
    with st.container(key="adv_section"):
        chosen = st.segmented_control(
            t("adv.nav_label"),
            sections,
            default=current if current in sections else "overview",
            format_func=lambda s: t(f"adv.sec_{s}"),
            label_visibility="collapsed",
            key=f"adv_section_ctl_{current}",
        )
    if chosen and chosen != current:
        st.session_state.adv_section = chosen
        st.rerun()

    if current == "positions":
        _client_positions(advisor, name, profile)
    elif not st.session_state.positions:
        st.info(t("adv.no_positions"))
    else:
        _client_analysis(advisor, name, profile, current, (period, in_eur, risk_free))
    compliance_footer()


def _client_analysis(
    advisor: str, name: str, profile: str, section: str, params: tuple[str, bool, float]
) -> None:
    ctx, error, notice = _context(advisor, name, profile, *params)
    if error:
        st.error(error)
        return
    if notice:
        st.warning(notice)
    if section == "analysis":
        _sub_tabs(ctx, [("nav.metrics", metrics.render), ("nav.charts", visual.render)])
    elif section == "strategies":
        _sub_tabs(
            ctx,
            [
                ("nav.optimization", optimize.render),
                ("nav.backtest", backtest.render),
                ("nav.options", options_overlay.render),
            ],
        )
    else:
        checkup.render(ctx)


def _sub_tabs(ctx: ViewContext, tabs: list[tuple[str, Callable[[ViewContext], None]]]) -> None:
    labels = [key for key, _ in tabs]
    with st.container(key="adv_sub"):
        chosen = st.segmented_control(
            t("adv.nav_label"),
            labels,
            default=labels[0],
            format_func=t,
            label_visibility="collapsed",
            key=f"adv_sub_{st.session_state.get('adv_section')}",
        )
    dict(tabs)[chosen or labels[0]](ctx)


def _client_positions(advisor: str, name: str, profile: str) -> None:
    pe.inject_css()
    with st.container(border=True):
        tab_manual, tab_import = st.tabs([t("gate.tab_manual"), t("gate.tab_import")])
        with tab_manual:
            pe.manual_entry("adv")
        with tab_import:
            pe.file_import("adv")
    pe.positions_table("adv", empty_hint=t("adv.empty_positions"))

    sec(t("side.risk_profile"))
    profile_col, save_col, _rest = st.columns([1.4, 1, 2], vertical_alignment="bottom")
    profile_col.selectbox(
        t("side.risk_profile"),
        RISK_PROFILES,
        index=RISK_PROFILES.index(profile) if profile in RISK_PROFILES else 0,
        key="adv_profile_edit",
        format_func=lambda p: t(f"prof.{p}"),
        label_visibility="collapsed",
    )
    save_col.button(
        t("side.save"), key="adv_profile_save", on_click=_save_profile, args=(advisor, name)
    )

    sec(t("adv.danger_title"))
    confirm = st.checkbox(t("side.delete_confirm", name=name), key="del_confirm")
    st.button(
        t("side.delete_btn"),
        key="adv_delete",
        disabled=not confirm,
        on_click=_delete_client,
        args=(advisor, name),
    )


def _page_market(advisor: str, period: str, in_eur: bool, risk_free: float) -> None:
    _page_header(t("adv.nav_market"), meta=t("adv.market_sub"))
    ctx = ViewContext(
        computed=None,
        amounts={},
        total=0.0,
        portfolio=[],
        portfolio_name="",
        period=period,
        in_eur=in_eur,
        risk_free=risk_free,
        risk_profile="Not set",
        advisor=advisor,
    )
    _sub_tabs(
        ctx,
        [
            ("nav.nasdaq", market.render),
            ("nav.correlations", correlations.render),
            ("nav.fundamentals", fundamentals.render),
        ],
    )


def _page_admin(advisor: str, period: str, in_eur: bool, risk_free: float) -> None:
    _page_header(t("adv.nav_admin"), meta=t("adv.admin_sub"))
    admin.render(
        ViewContext(
            computed=None,
            amounts={},
            total=0.0,
            portfolio=[],
            portfolio_name="",
            period=period,
            in_eur=in_eur,
            risk_free=risk_free,
            risk_profile="Not set",
            advisor=advisor,
        )
    )


# ------------------------------------------------------------------ ingresso


def render(advisor: str) -> None:
    """Disegna lo spazio di lavoro Advisor per il consulente corrente."""
    st.session_state.setdefault("adv_page", "clients")
    st.session_state.setdefault("positions", {})
    st.markdown(WORKSPACE_CSS, unsafe_allow_html=True)

    clients = list_clients(advisor)
    # cliente attivo sparito (cancellato altrove): si torna al book
    if st.session_state.adv_page == "client" and st.session_state.get("adv_client") not in clients:
        st.session_state.adv_page = "clients"
        st.session_state.adv_client = None
    if st.session_state.adv_page == "admin" and not is_admin(advisor):
        st.session_state.adv_page = "clients"

    period, in_eur, risk_free = _render_rail(advisor, clients)

    page = st.session_state.adv_page
    if page == "client":
        _page_client(advisor, clients, period, in_eur, risk_free)
        return  # il footer di conformità è già nella scheda cliente
    if page == "new_client":
        _page_new_client(advisor, clients)
    elif page == "market":
        _page_market(advisor, period, in_eur, risk_free)
    elif page == "admin":
        _page_admin(advisor, period, in_eur, risk_free)
    else:
        _page_clients(advisor, clients, period, in_eur)
    legal_footer()
