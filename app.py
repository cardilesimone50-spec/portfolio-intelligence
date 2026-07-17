"""SmarteeFinance — Portfolio Intelligence: the honest 60-second portfolio check-up.

Avvio: streamlit run app.py

app.py è solo il router: tema, gate di onboarding, sidebar, pipeline di calcolo
e dispatch alle viste in src/views/. La logica sta nei moduli, non qui.
"""

import os

import streamlit as st

from src.analytics.pipeline import analyze_portfolio
from src.data import yahoo_client
from src.data.fx import convert_to_eur
from src.i18n import set_language, t
from src.portfolio.positions import normalize_portfolio, position_table, totals
from src.ui.components import compliance_footer, empty_state
from src.ui.identity import current_advisor
from src.ui.theme import inject_theme
from src.views import (
    backtest,
    checkup,
    clients,
    correlations,
    fundamentals,
    gate,
    market,
    metrics,
    optimize,
    visual,
)
from src.views.common import BENCHMARK, cached_eurusd, cached_fundamentals, cached_prices
from src.views.context import ViewContext
from src.views.sidebar import render_sidebar

# ponte secrets→ambiente: i secrets di Streamlit non diventano env var da soli.
# Impostando DATABASE_URL nei secrets, lo store passa da SQLite a Postgres.
try:
    if "DATABASE_URL" in st.secrets:
        os.environ.setdefault("DATABASE_URL", str(st.secrets["DATABASE_URL"]))
except Exception:  # noqa: BLE001 — nessun secrets.toml in locale: si resta su SQLite
    pass

st.set_page_config(
    page_title="SmarteeFinance · Portfolio Intelligence",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_theme()

if "positions" not in st.session_state:
    st.session_state.positions = {}

# lingua dell'interfaccia: scelta persistita in sessione, default inglese
set_language(st.session_state.get("language", "en"))

# ================================================================ ONBOARDING GATE
gate.render_gate()  # se il gate è attivo, disegna lo stage e chiama st.stop()

# consulente corrente (tenant): portafogli e analisi sono isolati per advisor
advisor = current_advisor()
settings = render_sidebar(advisor)

positions = normalize_portfolio(st.session_state.positions)

# ================================================================ SHARED COMPUTATIONS
# posizioni → prezzi → valori attuali e P&L → pesi → pipeline di analisi
computed: dict | None = None
compute_error: str | None = None
amounts: dict[str, float] = {}
total = 0.0
portfolio: list = []
pos_table = None
pnl_totals = None
if positions:
    try:
        tickers = tuple(sorted(positions))
        prices_native = cached_prices(tickers, settings.period)
        bench_prices = cached_prices((BENCHMARK,), settings.period)
        if settings.in_eur:
            eurusd = cached_eurusd(settings.period)
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
        fund = cached_fundamentals(tickers)
        computed = analyze_portfolio(prices, bench_prices, portfolio, fund, BENCHMARK)
        if "name" in fund.columns:
            st.session_state["names"] = {
                **st.session_state.get("names", {}),
                **fund["name"].dropna().to_dict(),
            }
    except ValueError as exc:
        compute_error = str(exc)

# ================================================================ HEADER + NAV
st.markdown(
    f"""<div class="topbar">
    <span class="brand">◆ SMARTEE<b>FINANCE</b><span class="brand-product">Portfolio Intelligence</span></span>
    <span class="brand-tag">{t("top.eur") if settings.in_eur else t("top.orig")}
    · {t("top.source")}: {yahoo_client.last_price_source}</span></div>""",
    unsafe_allow_html=True,
)

# nav a due livelli: 5 voci macro + sub-nav contestuale che rimappa alla vista.
# Le voci mostrate sono tradotte; le chiavi interne restano stabili.
# (Home non è più qui: è il gate di onboarding che precede la piattaforma)
MACRO_LABELS = {
    "Check-up": t("nav.checkup"),
    "Analysis": t("nav.analysis"),
    "Strategies": t("nav.strategies"),
    "Market": t("nav.market"),
    "Clients": t("nav.clients"),
}
SUBNAV = {
    "Analysis": [(t("nav.metrics"), "Analisi"), (t("nav.charts"), "Visual")],
    "Strategies": [(t("nav.optimization"), "Ottimizza"), (t("nav.backtest"), "Backtest")],
    "Market": [
        (t("nav.nasdaq"), "Mercato"),
        (t("nav.correlations"), "Correlazioni"),
        (t("nav.fundamentals"), "Fondamentali"),
    ],
}
_label_to_macro = {label: key for key, label in MACRO_LABELS.items()}

with st.container(key="navbar"):
    macro_label = st.segmented_control(
        "Section",
        list(MACRO_LABELS.values()),
        default=MACRO_LABELS["Check-up"],
        label_visibility="collapsed",
        key=f"nav_{st.session_state.get('language', 'en')}",
    )
macro = _label_to_macro.get(macro_label or MACRO_LABELS["Check-up"], "Check-up")

if macro in SUBNAV:
    labels = [label for label, _ in SUBNAV[macro]]
    with st.container(key="subnav"):
        sub = st.segmented_control(
            "Subsection",
            labels,
            default=labels[0],
            label_visibility="collapsed",
            key=f"sub_{macro}_{st.session_state.get('language', 'en')}",
        )
    view = dict(SUBNAV[macro]).get(sub or labels[0], SUBNAV[macro][0][1])
else:
    view = macro

if compute_error:
    st.error(compute_error)

# ================================================================ DISPATCH
VIEWS = {
    "Check-up": checkup.render,
    "Analisi": metrics.render,
    "Visual": visual.render,
    "Ottimizza": optimize.render,
    "Backtest": backtest.render,
    "Mercato": market.render,
    "Correlazioni": correlations.render,
    "Fondamentali": fundamentals.render,
    "Clients": clients.render,
}
NEEDS_PORTFOLIO = {"Check-up", "Analisi", "Visual", "Ottimizza"}

ctx = ViewContext(
    computed=computed,
    amounts=amounts,
    total=total,
    portfolio=portfolio,
    portfolio_name=settings.portfolio_name,
    period=settings.period,
    in_eur=settings.in_eur,
    risk_free=settings.risk_free,
    risk_profile=settings.risk_profile,
    advisor=advisor,
    names=st.session_state.get("names", {}),
    pos=pos_table,
    pnl_totals=pnl_totals,
)

if view in NEEDS_PORTFOLIO and computed is None:
    if not compute_error:
        empty_state(t("app.empty_title"), t("app.empty_hint"))
else:
    VIEWS[view](ctx)

# ============================================================ COMPLIANCE FOOTER
compliance_footer()
