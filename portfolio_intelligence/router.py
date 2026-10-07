"""Logica condivisa tra app_investor.py e app_advisor.py.

I due entry point sono prodotti distinti (B2C anonimo/stateless vs B2B
multi-tenant/stateful) ma condividono lo stesso motore di calcolo. Qui vive
tutto ciò che è davvero identico tra i due: setup pagina, gate di
autenticazione, pipeline prezzi→analisi, meccanica di nav/dispatch. La
*struttura* della nav (quali tab, quali viste) resta nei due file, perché lì
sono i profili a differire per davvero — non ha senso nasconderla dietro
parametri generici.
"""

import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass

import pandas as pd
import streamlit as st

from portfolio_intelligence.analytics.pipeline import analyze_portfolio
from portfolio_intelligence.data.benchmarks import benchmark_label
from portfolio_intelligence.data.fx import convert_to_eur
from portfolio_intelligence.i18n import t
from portfolio_intelligence.logging_config import get_logger
from portfolio_intelligence.portfolio import Portfolio
from portfolio_intelligence.portfolio.positions import portfolio_xirr, position_table, totals
from portfolio_intelligence.ui.brand import page_icon
from portfolio_intelligence.ui.components import empty_state
from portfolio_intelligence.ui.identity import auth_required_but_missing, resolve_require_auth
from portfolio_intelligence.ui.legal import render_legal_page_if_requested, sync_document_language
from portfolio_intelligence.ui.theme import inject_theme
from portfolio_intelligence.views.common import (
    analysis_fundamentals,
    cached_eurusd,
    cached_prices,
    stored_benchmark,
)
from portfolio_intelligence.views.context import ViewContext
from portfolio_intelligence.views.sidebar import SidebarSettings

log = get_logger(__name__)


def bootstrap_page(page_title: str, require_auth_default: bool) -> None:
    """Bridge secrets→env, set_page_config, tema, gate REQUIRE_AUTH.

    `require_auth_default` è il valore di REQUIRE_AUTH se né l'operatore né
    i secrets lo scelgono esplicitamente: True per Advisor (B2B, l'auth è la
    norma), False per Investor (B2C anonimo, l'auth non si applica). La
    precedenza reale (env > secrets `[auth].require_auth` > questo default)
    è in `resolve_require_auth`.
    """
    # per sessione, mai scritto nell'ambiente: Investor e Advisor condividono il processo
    require_auth = resolve_require_auth(require_auth_default)

    # i secrets di Streamlit non diventano env var da soli: DATABASE_URL nei
    # secrets fa passare lo store da SQLite a Postgres.
    try:
        # SEC_USER_AGENT: contatto dichiarato alla SEC (policy di accesso EDGAR)
        for key in ("DATABASE_URL", "SEC_USER_AGENT"):
            if key in st.secrets:
                os.environ.setdefault(key, str(st.secrets[key]))
    except Exception:  # noqa: BLE001 — nessun secrets.toml in locale: si resta su SQLite
        pass

    st.set_page_config(
        page_title=page_title,
        page_icon=page_icon(),
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_theme()
    # i documenti legali devono essere leggibili anche senza login
    render_legal_page_if_requested()

    # gate duro: un deploy pubblico può imporre REQUIRE_AUTH=true per rifiutare
    # di servire richieste finché l'OIDC non isola davvero i dati per advisor
    if auth_required_but_missing(require_auth):
        st.error(
            "REQUIRE_AUTH is set but OIDC auth is not configured. "
            "Refusing to start: tenant data isolation cannot be guaranteed. "
            "Configure `[auth]` in secrets.toml before deploying."
        )
        st.stop()


def init_session() -> None:
    """Posizioni e lingua in session_state — stesso bootstrap per entrambi i profili."""
    if "positions" not in st.session_state:
        st.session_state.positions = {}
    from portfolio_intelligence.i18n import set_language

    set_language(st.session_state.get("language", "en"))
    sync_document_language(st.session_state.get("language", "en"))


@dataclass
class ComputedPortfolio:
    computed: dict | None
    compute_error: str | None
    amounts: dict[str, float]
    total: float
    portfolio: Portfolio
    pos_table: pd.DataFrame | None
    pnl_totals: dict | None
    irr: float | None
    names: dict[str, str]
    notice: str | None = None  # avviso non bloccante (es. bilanci non disponibili)


def benchmark_prices(ticker: str, period: str) -> tuple[pd.DataFrame, str | None]:
    """Prezzi del benchmark scelto: (prezzi, avviso o None).

    Prima la serie live (catena di provider, in cache); se nessun provider
    risponde, lo storico salvato dall'ingestion, con un avviso che dichiara fino
    a che data arriva. Senza né l'una né l'altro solleva l'errore della catena.
    """
    try:
        return cached_prices((ticker,), period), None
    except ValueError:
        stored = stored_benchmark(ticker, period)
        if stored is None or stored.empty:
            raise
    log.warning("Live prices unavailable for benchmark %s, using the stored history", ticker)
    notice = t(
        "app.bench_stored",
        benchmark=benchmark_label(ticker),
        date=f"{stored.index[-1]:%d/%m/%Y}",
    )
    return stored, notice


def compute_portfolio(positions: dict, settings: SidebarSettings) -> ComputedPortfolio:
    """Pipeline condivisa: posizioni → prezzi → P&L → pesi → analyze_portfolio.

    Identica per Investor e Advisor: i dati di mercato (prezzi, fondamentali)
    sono riferimento condiviso, non stato per-advisor — nessuna scrittura sul
    DB qui, solo letture cachate.
    """
    computed: dict | None = None
    compute_error: str | None = None
    amounts: dict[str, float] = {}
    total = 0.0
    portfolio: Portfolio = []
    pos_table = None
    pnl_totals = None
    irr: float | None = None
    names: dict[str, str] = dict(st.session_state.get("names", {}))
    notices: list[str] = []

    if not positions:
        return ComputedPortfolio(
            computed, compute_error, amounts, total, portfolio, pos_table, pnl_totals, irr, names
        )

    try:
        tickers = tuple(sorted(positions))
        with st.spinner(t("app.loading_data")):
            prices_native = cached_prices(tickers, settings.period)
            bench_prices, bench_notice = benchmark_prices(settings.benchmark, settings.period)
            eurusd = cached_eurusd(settings.period) if settings.in_eur else None
        if settings.in_eur:
            prices = convert_to_eur(prices_native, eurusd)
            bench_prices = convert_to_eur(bench_prices, eurusd)
        else:
            prices = prices_native
        # fattore FX per ticker all'ultima data: converte carico e valore
        # alla valuta di visualizzazione senza toccare il P&L percentuale
        last_native = prices_native.ffill().iloc[-1]
        last_display = prices.ffill().iloc[-1]
        fx_factor = (last_display / last_native).fillna(1.0)
        pos_table = position_table(positions, last_native, fx_factor)
        pnl_totals = totals(pos_table)
        irr = portfolio_xirr(positions, last_native, fx_factor)
        amounts = {
            ticker: float(value)
            for ticker, value in pos_table["value"].items()
            if value == value and value > 0
        }
        total = sum(amounts.values())
        portfolio = (
            [{"ticker": t_, "weight": amount / total} for t_, amount in amounts.items()]
            if total
            else []
        )
        fund = analysis_fundamentals(tickers)
        computed = analyze_portfolio(prices, bench_prices, portfolio, fund, settings.benchmark)
        if bench_notice:
            notices.append(bench_notice)
        if fund.isna().all().all():
            notices.append(t("app.fund_unavailable"))
        if "name" in fund.columns:
            names = {**names, **fund["name"].dropna().to_dict()}
            st.session_state["names"] = names
    except ValueError as exc:
        compute_error = str(exc)

    return ComputedPortfolio(
        computed,
        compute_error,
        amounts,
        total,
        portfolio,
        pos_table,
        pnl_totals,
        irr,
        names,
        " ".join(notices) or None,
    )


def render_header(in_eur: bool, product_tag: str) -> None:
    from portfolio_intelligence.data import yahoo_client

    st.markdown(
        f"""<div class="topbar">
        <span class="brand">SMARTEE<b>FINANCE</b><span class="brand-product">{product_tag}</span></span>
        <span class="brand-tag">{t("top.eur") if in_eur else t("top.orig")}
        · {t("top.source")}: {yahoo_client.last_price_source}</span></div>""",
        unsafe_allow_html=True,
    )


def render_nav_and_dispatch(
    macro_labels: dict[str, str],
    subnav: dict[str, list[tuple[str, str]]],
    views: Mapping[str, Callable[[ViewContext], None]],
    needs_portfolio: set[str],
    ctx: ViewContext,
    compute_error: str | None,
    notice: str | None = None,
) -> None:
    """Meccanica di nav a due livelli + dispatch: identica tra i profili.

    `macro_labels`/`subnav`/`views`/`needs_portfolio` sono la DATA che
    differisce per davvero tra Investor e Advisor (quali tab, quali viste) —
    qui c'è solo il motore che le rende, non le scelte di prodotto.
    """
    default_macro = next(iter(macro_labels))
    label_to_macro = {label: key for key, label in macro_labels.items()}

    with st.container(key="navbar"):
        macro_label = st.segmented_control(
            "Section",
            list(macro_labels.values()),
            default=macro_labels[default_macro],
            label_visibility="collapsed",
            key=f"nav_{st.session_state.get('language', 'en')}",
        )
    macro = label_to_macro.get(macro_label or macro_labels[default_macro], default_macro)

    if macro in subnav:
        labels = [label for label, _ in subnav[macro]]
        with st.container(key="subnav"):
            sub = st.segmented_control(
                "Subsection",
                labels,
                default=labels[0],
                label_visibility="collapsed",
                key=f"sub_{macro}_{st.session_state.get('language', 'en')}",
            )
        view = dict(subnav[macro]).get(sub or labels[0], subnav[macro][0][1])
    else:
        view = macro

    if compute_error:
        st.error(compute_error)
    elif notice:
        st.warning(notice)

    if view in needs_portfolio and ctx.computed is None:
        if not compute_error:
            empty_state(t("app.empty_title"), t("app.empty_hint"))
    else:
        views[view](ctx)
