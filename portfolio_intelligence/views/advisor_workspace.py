"""Spazio di lavoro dell'area Advisor: un'interfaccia da consulente, non da investitore.

Struttura (diversa da Investor, che è un percorso guidato per un solo portafoglio):
- navigazione a sinistra: Clienti, Nuovo cliente, il cliente attivo con le sue
  sezioni, Mercato, Amministrazione; in basso parametri, privacy e lingua;
- Clienti (pagina iniziale): il book con indicatori sintetici e una riga per
  cliente, ordinato da chi richiede attenzione per primo;
- Nuovo cliente: codice, profilo di rischio dichiarato, benchmark di riferimento e posizioni;
- scheda cliente: intestazione con profilo e stato, sezioni Panoramica,
  Posizioni, Analisi, Strategie. Le viste di analisi sono le stesse di
  Investor, ma lavorano sul cliente e salvano su DB, isolate per consulente.

Stato di sessione: `adv_page`, `adv_client` (codice del cliente attivo),
`adv_saved` (le posizioni salvate, per riconoscere le modifiche),
`adv_profile`/`adv_benchmark` (profilo e benchmark di lavoro, con i salvati in
`adv_saved_profile`/`adv_saved_benchmark`) e `positions` (il portafoglio di
lavoro, condiviso con le viste).
"""

import html
import json
from collections.abc import Callable

import pandas as pd
import streamlit as st

from portfolio_intelligence.config import (
    ADVISOR_HISTORY_PERIOD,
    DEFAULT_RISK_PROFILE,
    HEALTH_SCORE_FAIR,
    RISK_PROFILES,
)
from portfolio_intelligence.data.benchmarks import (
    BENCHMARK_TICKERS,
    BENCHMARKS,
    DEFAULT_BENCHMARK,
    benchmark_label,
)
from portfolio_intelligence.data.store import (
    REDACTED,
    ClientExistsError,
    create_client,
    delete_advisor_data,
    delete_portfolio,
    list_clients,
    log_audit,
    save_portfolio,
)
from portfolio_intelligence.data.validators import is_valid_client_code
from portfolio_intelligence.formatting import missing
from portfolio_intelligence.i18n import get_language, period_text, t
from portfolio_intelligence.portfolio.positions import normalize_portfolio
from portfolio_intelligence.router import compute_portfolio
from portfolio_intelligence.ui.area_switch import area_switch
from portfolio_intelligence.ui.components import compliance_footer, eur, pct, sec, text_safe
from portfolio_intelligence.ui.identity import auth_configured, is_admin, is_authenticated
from portfolio_intelligence.ui.legal import legal_footer
from portfolio_intelligence.views import (
    admin,
    advisor_overview,
    backtest,
    correlations,
    fundamentals,
    market,
    metrics,
    monte_carlo,
    optimize,
    options_overlay,
    visual,
)
from portfolio_intelligence.views import portfolio_editor as pe
from portfolio_intelligence.views.clients import quick_client_analysis, status_color
from portfolio_intelligence.views.common import PROFILE_VOL, SAMPLE_PORTFOLIO, language_selector
from portfolio_intelligence.views.context import ViewContext
from portfolio_intelligence.views.sidebar import SidebarSettings, analysis_parameters

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

/* ---- intestazione di pagina ---- */
.adv-head { padding: var(--s-2) 0 var(--s-4); border-bottom: 1px solid var(--line);
            margin-bottom: var(--s-5); }
.adv-head.bare { border-bottom: none; margin-bottom: 0; padding-bottom: var(--s-2); }
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
    display: grid; grid-template-columns: 1.3fr 1fr 1.1fr 0.9fr 0.9fr 1fr 0.7fr 2.6fr;
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
.book-grid .over { color: var(--loss); font-weight: 700; }
.book-grid .pending { font-size: 0.75rem; font-weight: 600; color: var(--ink-2); margin-left: 16px; }
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
#
# Le modifiche non salvate non si perdono navigando: lasciando la scheda di un
# cliente, posizioni, profilo e benchmark di lavoro finiscono in `adv_drafts[cliente]` e
# tornano alla riapertura, finché non si salva o si annulla. Le bozze vivono
# solo nella sessione del browser, mai nel database.


# il predefinito per primo: è la scelta iniziale del selettore
BENCHMARK_OPTIONS = [DEFAULT_BENCHMARK, *(b for b in BENCHMARK_TICKERS if b != DEFAULT_BENCHMARK)]


def _benchmark_option(ticker: str) -> str:
    """Voce del selettore: nome esteso, con la natura della serie se esclude i dividendi."""
    benchmark = BENCHMARKS[ticker]
    if benchmark.total_return:
        return benchmark.name
    return f"{benchmark.name} · {t('bench.price_index')}"


def _fingerprint(positions: dict) -> str:
    return json.dumps(positions, sort_keys=True, default=str)


def _drafts() -> dict[str, dict]:
    return st.session_state.setdefault("adv_drafts", {})


def is_dirty() -> bool:
    """Posizioni, profilo o benchmark del cliente attivo diversi da quelli salvati."""
    if st.session_state.get("adv_page") != "client" or not st.session_state.get("adv_client"):
        return False
    state = st.session_state
    return (
        _fingerprint(state.positions) != state.get("adv_saved")
        or state.get("adv_profile") != state.get("adv_saved_profile")
        or state.get("adv_benchmark") != state.get("adv_saved_benchmark")
    )


def _stash() -> None:
    """Prima di cambiare pagina: mette da parte il lavoro in corso, se c'è."""
    page = st.session_state.get("adv_page")
    if page == "client" and (name := st.session_state.get("adv_client")):
        if is_dirty():
            _drafts()[name] = {
                "positions": dict(st.session_state.positions),
                "profile": st.session_state.get("adv_profile", DEFAULT_RISK_PROFILE),
                "benchmark": st.session_state.get("adv_benchmark", DEFAULT_BENCHMARK),
            }
        else:
            _drafts().pop(name, None)
    elif page == "new_client":
        st.session_state.adv_new_draft = dict(st.session_state.positions)


def _goto(page: str) -> None:
    _stash()
    st.session_state.adv_page = page


def _new_client() -> None:
    _stash()
    st.session_state.adv_page = "new_client"
    st.session_state.adv_client = None
    st.session_state.positions = dict(st.session_state.get("adv_new_draft") or {})


def _open_client(
    name: str, positions: dict, profile: str, benchmark: str, section: str = "overview"
) -> None:
    if st.session_state.get("adv_page") != "client" or st.session_state.get("adv_client") != name:
        _stash()
    saved = normalize_portfolio(positions)
    draft = _drafts().get(name)
    st.session_state.adv_page = "client"
    st.session_state.adv_client = name
    st.session_state.adv_section = section
    st.session_state.adv_saved = _fingerprint(saved)
    st.session_state.adv_saved_profile = profile
    st.session_state.adv_saved_benchmark = benchmark
    st.session_state.positions = dict(draft["positions"]) if draft else saved
    st.session_state.adv_profile = draft["profile"] if draft else profile
    st.session_state.adv_benchmark = draft.get("benchmark", benchmark) if draft else benchmark


def _goto_section(section: str) -> None:
    st.session_state.adv_page = "client"
    st.session_state.adv_section = section


def _discard_changes(saved_positions: dict, saved_profile: str, saved_benchmark: str) -> None:
    name = st.session_state.adv_client
    _drafts().pop(name, None)
    st.session_state.positions = normalize_portfolio(saved_positions)
    st.session_state.adv_profile = saved_profile
    st.session_state.adv_benchmark = saved_benchmark
    # i selettori ripartono dai valori salvati, non dall'ultima scelta annullata
    st.session_state.pop(f"adv_profile_sel_{name}", None)
    st.session_state.pop(f"adv_bench_sel_{name}", None)


def _forget(names: list[str]) -> None:
    for name in names:
        _drafts().pop(name, None)
        st.session_state.get("adv_recipients", {}).pop(name, None)


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
            '<div class="brand adv-brand">SMARTEE<b>FINANCE</b>'
            f'<span class="brand-product">{t("adv.product")}</span></div>',
            unsafe_allow_html=True,
        )
        area_switch("advisor", "area_sw_rail")
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
            pending = is_dirty() or client in _drafts()
            label = f"{client} · {t('adv.unsaved_short')}" if pending else client
            _nav_button("client", label, _goto_section, (section,))
        st.markdown('<div class="adv-rail-label"></div>', unsafe_allow_html=True)
        _nav_button("market", t("adv.nav_market"), _goto, ("market",))
        if is_admin(advisor):
            _nav_button("admin", t("adv.nav_admin"), _goto, ("admin",))

        with st.expander(t("adv.params")):
            period, in_eur, risk_free = analysis_parameters("adv", ADVISOR_HISTORY_PERIOD)
        with st.expander(t("side.privacy")):
            st.caption(t("side.erase_all_hint"))
            confirm_all = st.checkbox(t("side.erase_all_confirm"), key="erase_all_confirm")
            if st.button(t("side.erase_all_btn"), width="stretch", disabled=not confirm_all):
                counts = delete_advisor_data(advisor)
                _forget(list(clients))
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
    return period, in_eur, risk_free


def _page_header(
    title: str, crumb: str | None = None, meta: str | None = None, rule: bool = True
) -> None:
    st.markdown(
        f'<div class="adv-head{"" if rule else " bare"}">'
        + (f'<div class="adv-crumb">{crumb}</div>' if crumb else "")
        + f'<h1 class="page-title adv-title">{html.escape(title)}</h1>'
        + (f'<div class="adv-meta">{html.escape(meta)}</div>' if meta else "")
        + "</div>",
        unsafe_allow_html=True,
    )


def _context(
    advisor: str,
    name: str,
    profile: str,
    benchmark: str,
    period: str,
    in_eur: bool,
    risk_free: float,
) -> tuple[ViewContext, str | None, str | None]:
    positions = normalize_portfolio(st.session_state.positions)
    settings = SidebarSettings(name, period, in_eur, risk_free, profile, benchmark)
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
        benchmark=benchmark,
    )
    return ctx, cp.compute_error, cp.notice


# ------------------------------------------------------------------ pagine


def _book_rows(clients: dict, period: str, in_eur: bool) -> list[dict]:
    rows = []
    for name, record in clients.items():
        row = {
            "name": name,
            "profile": record["risk_profile"],
            "benchmark": record["benchmark"],
            "positions": record["positions"],
        }
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
        vol_out = "error" not in row and band is not None and row["vol"] > band
        health_low = "error" not in row and row["health"] < HEALTH_SCORE_FAIR
        row["review"] = vol_out or health_low
        if row["review"] and row["problem"] == t("chk.no_problems"):
            # da rivedere senza un problema dalle regole: si mostra il motivo della revisione
            row["problem"] = (
                t(
                    "adv.review_vol",
                    vol=pct(row["vol"]),
                    band=pct(band, 0),
                    profile=t(f"prof.{record['risk_profile']}").lower(),
                )
                if vol_out
                else t("adv.review_health", health=row["health"], fair=HEALTH_SCORE_FAIR)
            )
        rows.append(row)
    # chi richiede attenzione per primo: da rivedere, poi Health crescente
    return sorted(rows, key=lambda r: (not r["review"], r.get("health", 101), r["name"]))


def _vol_cell(row: dict) -> str:
    """Volatilità del cliente; in evidenza se supera il limite del suo profilo."""
    band = PROFILE_VOL.get(row["profile"])
    text = pct(row["vol"])
    if band is not None and row["vol"] > band:
        return f'<span class="over" title="{t("adv.over_limit", band=pct(band, 0))}">{text}</span>'
    return text


def _book_csv(rows: list[dict]) -> bytes:
    """Il book in CSV per il back office: una riga per cliente, numeri non formattati."""
    columns = [
        "name",
        "profile",
        "benchmark",
        "value",
        "invested",
        "pnl_pct",
        "vol",
        "drawdown",
        "top_ticker",
        "top_weight",
        "health",
        "review",
        "problem",
        "asof",
        "error",
    ]
    frame = pd.DataFrame([{k: r.get(k) for k in columns} for r in rows], columns=columns)
    return frame.to_csv(index=False).encode("utf-8")


def _create_demo(advisor: str) -> None:
    try:
        create_client(advisor, DEMO_CLIENT, SAMPLE_PORTFOLIO, risk_profile="Moderate")
    except ClientExistsError:
        pass  # già creato in precedenza: si apre quello, con i valori salvati
    else:
        log_audit(advisor, "create_client", DEMO_CLIENT)
    record = list_clients(advisor).get(DEMO_CLIENT) or {
        "positions": SAMPLE_PORTFOLIO,
        "risk_profile": "Moderate",
        "benchmark": DEFAULT_BENCHMARK,
    }
    _open_client(DEMO_CLIENT, record["positions"], record["risk_profile"], record["benchmark"])


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
        (t("adv.kpi_aum"), eur(aum) if analysed else "n/a", t("adv.kpi_aum_sub")),
        (
            t("adv.kpi_review"),
            str(sum(r["review"] for r in rows)),
            t("adv.kpi_review_sub", fair=HEALTH_SCORE_FAIR),
        ),
        (
            t("adv.kpi_health"),
            str(avg_health) if avg_health is not None else "n/a",
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

    asof = max((r["asof"] for r in analysed), default=None)
    if asof:
        st.caption(
            t("adv.book_asof", date=f"{pd.Timestamp(asof):%d/%m/%Y}", period=period_text(period))
        )
    search_col, _gap, export_col, new_col = st.columns([2, 0.6, 1, 1], vertical_alignment="bottom")
    query = search_col.text_input(
        t("adv.search"),
        key="adv_search",
        placeholder=t("adv.search"),
        label_visibility="collapsed",
    )
    export_col.download_button(
        t("adv.export_book"),
        data=_book_csv(rows),
        file_name=f"book_{pd.Timestamp.now():%Y%m%d}.csv",
        mime="text/csv",
        width="stretch",
        key="adv_export_book",
    )
    new_col.button(t("adv.nav_new"), type="primary", width="stretch", on_click=_new_client)
    pending = sorted(name for name in _drafts() if name in clients)
    if pending:
        st.warning(t("adv.pending_book", clients=", ".join(pending)))
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
        ("num", t("adv.col_top")),
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
    na = missing(get_language())
    for i, row in enumerate(shown):
        if "error" in row:
            data = [
                ("c-code", html.escape(row["name"])),
                ("", t(f"prof.{row['profile']}")),
                ("num", na),
                ("num", na),
                ("num", na),
                ("num", na),
                ("health", na),
                ("flag", html.escape(t("adv.analysis_failed", err=row["error"]))),
            ]
        else:
            color = status_color(row["health"])
            ret = row["pnl_pct"]  # senza prezzo di carico: n/d, mai il rendimento di periodo
            marker = (
                f'<div class="pending">{t("adv.unsaved_short")}</div>'
                if row["name"] in _drafts()
                else ""
            )
            data = [
                (
                    "c-code",
                    f'<span class="dot" style="background:{color}"></span>'
                    f"{html.escape(row['name'])}{marker}",
                ),
                ("", t(f"prof.{row['profile']}")),
                ("num", eur(row["value"])),
                (
                    "num " + ("up" if ret >= 0 else "down" if ret < 0 else ""),
                    pct(ret, signed=True),
                ),
                ("num", _vol_cell(row)),
                ("num", f"{row['top_ticker']} {pct(row['top_weight'], 0)}"),
                ("health", f'<span style="color:{text_safe(color)}">{row["health"]}</span>'),
                ("flag", html.escape(row["problem"])),
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
                args=(row["name"], row["positions"], row["profile"], row["benchmark"]),
            )


def _create_client(advisor: str) -> None:
    name = (st.session_state.get("adv_new_name") or "").strip()
    profile = st.session_state.get("adv_new_profile", DEFAULT_RISK_PROFILE)
    benchmark = st.session_state.get("adv_new_benchmark", DEFAULT_BENCHMARK)
    positions = dict(st.session_state.positions)
    if not name or not positions:
        return
    try:
        # il controllo dei duplicati sta nel database: un doppio clic o un'altra
        # scheda aperta non possono sovrascrivere un cliente esistente
        create_client(advisor, name, positions, risk_profile=profile, benchmark=benchmark)
    except ClientExistsError:
        st.session_state.adv_create_error = t("adv.code_exists")
        return
    log_audit(advisor, "create_client", name)
    st.session_state.adv_new_name = ""
    st.session_state.adv_new_profile = DEFAULT_RISK_PROFILE
    st.session_state.adv_new_benchmark = DEFAULT_BENCHMARK
    st.session_state.adv_new_draft = {}
    st.session_state.pop("adv_create_error", None)
    st.session_state.adv_page = "new_client"  # nessuna bozza da mettere da parte
    _open_client(name, positions, profile, benchmark)
    st.toast(t("adv.created", name=name))


def _page_new_client(advisor: str, clients: dict) -> None:
    pe.inject_css()
    _page_header(t("adv.new_title"), crumb=t("adv.nav_clients"), meta=t("adv.new_sub"))
    main, side = st.columns([2.4, 1], gap="large")
    with main:
        with st.container(border=True):
            sec(t("adv.registry"))
            code_col, profile_col, bench_col = st.columns([1.2, 1, 1.2])
            code_col.text_input(
                t("adv.client_code"), key="adv_new_name", help=t("adv.client_code_help")
            )
            profile_col.selectbox(
                t("side.risk_profile"),
                RISK_PROFILES,
                key="adv_new_profile",
                format_func=lambda p: t(f"prof.{p}"),
            )
            bench_col.selectbox(
                t("adv.benchmark"),
                BENCHMARK_OPTIONS,
                key="adv_new_benchmark",
                format_func=_benchmark_option,
                help=t("adv.benchmark_help"),
            )
            name = (st.session_state.get("adv_new_name") or "").strip()
            error = st.session_state.pop("adv_create_error", None)
            if name and not is_valid_client_code(name):
                st.error(t("adv.code_invalid"))
            elif name in clients or error:
                st.error(error or t("adv.code_exists"))
        with st.container(border=True):
            tab_manual, tab_import = st.tabs([t("gate.tab_manual"), t("gate.tab_import")])
            with tab_manual:
                pe.manual_entry("adv")
            with tab_import:
                pe.file_import("adv")
        pe.positions_table("adv", empty_hint=t("adv.empty_positions"))
    with side, st.container(border=True):
        positions = st.session_state.positions
        profile = st.session_state.get("adv_new_profile", DEFAULT_RISK_PROFILE)
        benchmark = st.session_state.get("adv_new_benchmark", DEFAULT_BENCHMARK)
        rows = [
            (t("adv.client_code"), name or missing(get_language())),
            (t("side.risk_profile"), t(f"prof.{profile}")),
            (t("adv.benchmark"), html.escape(benchmark_label(benchmark))),
            (t("gate.sum_positions"), str(len(positions))),
            (t("gate.sum_invested"), pe.invested_text(positions)),
        ]
        st.markdown(
            f'<div class="sum-h">{t("gate.summary")}</div>'
            + "".join(
                f'<div class="sum-row"><span class="k">{k}</span><span class="v">{v}</span></div>'
                for k, v in rows
            ),
            unsafe_allow_html=True,
        )
        ready = (
            bool(name) and is_valid_client_code(name) and bool(positions) and name not in clients
        )
        st.button(
            t("adv.create"),
            type="primary",
            width="stretch",
            disabled=not ready,
            help=None if ready else t("adv.create_disabled"),
            on_click=_create_client,
            args=(advisor,),
        )


def _save_changes(advisor: str, name: str) -> None:
    """Salva insieme posizioni, profilo e benchmark di lavoro del cliente attivo."""
    profile = st.session_state.get("adv_profile", DEFAULT_RISK_PROFILE)
    benchmark = st.session_state.get("adv_benchmark", DEFAULT_BENCHMARK)
    save_portfolio(
        advisor, name, st.session_state.positions, risk_profile=profile, benchmark=benchmark
    )
    log_audit(advisor, "save_portfolio", name)
    st.session_state.adv_saved = _fingerprint(st.session_state.positions)
    st.session_state.adv_saved_profile = profile
    st.session_state.adv_saved_benchmark = benchmark
    _drafts().pop(name, None)
    st.toast(t("adv.saved"))


def _delete_client(advisor: str, name: str) -> None:
    delete_portfolio(advisor, name)
    log_audit(advisor, "delete_portfolio", REDACTED)
    _forget([name])
    st.session_state.adv_client = None
    st.session_state.adv_page = "clients"
    st.session_state.positions = {}
    st.toast(t("side.deleted_toast"))


def _set_profile(name: str) -> None:
    st.session_state.adv_profile = st.session_state[f"adv_profile_sel_{name}"]


def _set_benchmark(name: str) -> None:
    st.session_state.adv_benchmark = st.session_state[f"adv_bench_sel_{name}"]


def _set_recipient(name: str) -> None:
    recipients = st.session_state.setdefault("adv_recipients", {})
    recipients[name] = st.session_state[f"adv_recipient_in_{name}"].strip()


def _page_client(advisor: str, clients: dict, period: str, in_eur: bool, risk_free: float) -> None:
    name = st.session_state.adv_client
    record = clients[name]
    saved_profile = record["risk_profile"]
    saved_benchmark = record["benchmark"]
    # sessione senza stato di lavoro per questo cliente (es. dopo un riavvio)
    if (
        st.session_state.get("adv_saved_profile") is None
        or "adv_profile" not in st.session_state
        or "adv_benchmark" not in st.session_state
    ):
        _open_client(
            name,
            record["positions"],
            saved_profile,
            saved_benchmark,
            st.session_state.get("adv_section", "overview"),
        )
    profile = st.session_state.adv_profile
    benchmark = st.session_state.adv_benchmark
    dirty = is_dirty()

    head_col, action_col = st.columns([4, 1], vertical_alignment="bottom")
    with head_col:
        _page_header(
            name,
            crumb=t("adv.nav_clients"),
            meta=t(
                "adv.meta",
                profile=t(f"prof.{saved_profile}"),
                benchmark=benchmark_label(saved_benchmark),
                n=len(record["positions"]),  # dati salvati, come profilo e data
                updated=f"{pd.Timestamp(record['updated']):%d/%m/%Y}",
            ),
            rule=False,  # la riga delle sezioni sotto fa già da separatore
        )
    with action_col:
        st.button(
            t("adv.save"),
            type="primary",
            width="stretch",
            disabled=not dirty,
            on_click=_save_changes,
            args=(advisor, name),
        )
    if dirty:
        warn_col, undo_col = st.columns([4, 1], vertical_alignment="center")
        warn_col.warning(t("adv.unsaved"))
        undo_col.button(
            t("adv.discard"),
            key="adv_discard",
            width="stretch",
            on_click=_discard_changes,
            args=(record["positions"], saved_profile, saved_benchmark),
        )

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
        _client_positions(advisor, name, profile, benchmark)
    elif not st.session_state.positions:
        st.info(t("adv.no_positions"))
    else:
        _client_analysis(advisor, name, profile, benchmark, current, (period, in_eur, risk_free))
    compliance_footer()


def _recipient_field(name: str) -> str:
    """Intestazione del PDF per il cliente: solo in sessione, mai nel database."""
    current = st.session_state.get("adv_recipients", {}).get(name, "")
    st.text_input(
        t("adv.recipient"),
        value=current,
        key=f"adv_recipient_in_{name}",
        placeholder=t("adv.recipient_placeholder"),
        on_change=_set_recipient,
        args=(name,),
    )
    return current


def _client_analysis(
    advisor: str,
    name: str,
    profile: str,
    benchmark: str,
    section: str,
    params: tuple[str, bool, float],
) -> None:
    ctx, error, notice = _context(advisor, name, profile, benchmark, *params)
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
                ("nav.montecarlo", monte_carlo.render),
            ],
        )
    else:
        advisor_overview.render(ctx, lambda: _recipient_field(name))


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


def _client_positions(advisor: str, name: str, profile: str, benchmark: str) -> None:
    pe.inject_css()
    with st.container(border=True):
        tab_manual, tab_import = st.tabs([t("gate.tab_manual"), t("gate.tab_import")])
        with tab_manual:
            pe.manual_entry("adv")
        with tab_import:
            pe.file_import("adv")
    pe.positions_table("adv", empty_hint=t("adv.empty_positions"))

    sec(t("side.risk_profile"))
    profile_col, note_col = st.columns([1.4, 3], vertical_alignment="center")
    # chiave per cliente: il valore scelto per un cliente non può comparire su un altro
    profile_col.selectbox(
        t("side.risk_profile"),
        RISK_PROFILES,
        index=RISK_PROFILES.index(profile) if profile in RISK_PROFILES else 0,
        key=f"adv_profile_sel_{name}",
        format_func=lambda p: t(f"prof.{p}"),
        label_visibility="collapsed",
        on_change=_set_profile,
        args=(name,),
    )
    note_col.caption(t("adv.profile_note"))

    sec(t("adv.benchmark"))
    bench_col, bench_note_col = st.columns([1.4, 3], vertical_alignment="center")
    # stessa regola del profilo: chiave per cliente, la scelta resta di quel cliente
    bench_col.selectbox(
        t("adv.benchmark"),
        BENCHMARK_OPTIONS,
        index=BENCHMARK_OPTIONS.index(benchmark) if benchmark in BENCHMARK_OPTIONS else 0,
        key=f"adv_bench_sel_{name}",
        format_func=_benchmark_option,
        help=t("adv.benchmark_help"),
        label_visibility="collapsed",
        on_change=_set_benchmark,
        args=(name,),
    )
    bench_note_col.caption(t("adv.benchmark_note"))

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
        _forget([st.session_state.get("adv_client") or ""])
        st.session_state.adv_page = "clients"
        st.session_state.adv_client = None
    _forget([name for name in list(_drafts()) if name not in clients])
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
