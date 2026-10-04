"""Smarteefinance Advisor — Portfolio Intelligence professionale per il consulente B2B.

Avvio: streamlit run app_advisor.py

Stateful, multi-tenant, OIDC obbligatoria per impostazione predefinita (si
può disattivare solo esplicitamente con REQUIRE_AUTH=false nell'ambiente —
mai per difetto, un deploy pubblico senza auth non isola i dati). Portafogli,
analisi e audit log persistono sul DB (SQLite in locale, Postgres in
produzione via DATABASE_URL) isolati per `current_advisor()`.

Navigazione completa: dashboard clienti, posizioni a lotti con IRR/XIRR
reale, ottimizzazione di Markowitz, backtest con costi di transazione,
overlay di opzioni protettive, e — per gli indirizzi in `admin_emails` —
statistiche cross-tenant e audit log.
"""

import streamlit as st

from portfolio_intelligence.i18n import t
from portfolio_intelligence.portfolio.positions import normalize_portfolio
from portfolio_intelligence.router import (
    bootstrap_page,
    compute_portfolio,
    init_session,
    render_header,
    render_nav_and_dispatch,
)
from portfolio_intelligence.ui.components import compliance_footer
from portfolio_intelligence.ui.identity import current_advisor, is_admin
from portfolio_intelligence.views import (
    admin,
    backtest,
    checkup,
    clients,
    correlations,
    fundamentals,
    gate,
    market,
    metrics,
    optimize,
    options_overlay,
    visual,
)
from portfolio_intelligence.views.advisor_welcome import render_advisor_gate
from portfolio_intelligence.views.context import ViewContext
from portfolio_intelligence.views.sidebar import render_sidebar


def main() -> None:
    bootstrap_page("Smarteefinance Advisor | Professional Portfolio Intelligence", True)
    init_session()

    # consulente corrente (tenant): portafogli e analisi sono isolati per advisor
    advisor = current_advisor()

    # =============================================== LOGIN GATE / WELCOME WORKSPACE
    # login istituzionale (non autenticato) o console di benvenuto con KPI e
    # quick action (prima volta nella sessione) — st.stop() internamente finché
    # non si procede. Non tocca Investor: è specifico di app_advisor.py.
    render_advisor_gate(advisor)

    # ================================================================ ONBOARDING GATE
    gate.render_gate()  # se il gate è attivo, disegna lo stage e chiama st.stop()

    settings = render_sidebar(advisor, advisor_mode=True)

    positions = normalize_portfolio(st.session_state.positions)
    cp = compute_portfolio(positions, settings)

    render_header(settings.in_eur, "Advisor")

    # nav a due livelli: 5 voci macro + sub-nav contestuale che rimappa alla
    # vista. (Home non è qui: è il gate di onboarding che precede la piattaforma)
    macro_labels = {
        "Check-up": t("nav.checkup"),
        "Analysis": t("nav.analysis"),
        "Strategies": t("nav.strategies"),
        "Market": t("nav.market"),
        "Clients": t("nav.clients"),
    }
    if is_admin(advisor):
        macro_labels["Admin"] = t("nav.admin")
    subnav = {
        "Analysis": [(t("nav.metrics"), "Analisi"), (t("nav.charts"), "Visual")],
        "Strategies": [
            (t("nav.optimization"), "Ottimizza"),
            (t("nav.backtest"), "Backtest"),
            (t("nav.options"), "Opzioni"),
        ],
        "Market": [
            (t("nav.nasdaq"), "Mercato"),
            (t("nav.correlations"), "Correlazioni"),
            (t("nav.fundamentals"), "Fondamentali"),
        ],
    }
    views = {
        "Check-up": checkup.render,
        "Analisi": metrics.render,
        "Visual": visual.render,
        "Ottimizza": optimize.render,
        "Opzioni": options_overlay.render,
        "Backtest": backtest.render,
        "Mercato": market.render,
        "Correlazioni": correlations.render,
        "Fondamentali": fundamentals.render,
        "Clients": clients.render,
        "Admin": admin.render,
    }
    needs_portfolio = {"Check-up", "Analisi", "Visual", "Ottimizza", "Opzioni"}

    ctx = ViewContext(
        computed=cp.computed,
        amounts=cp.amounts,
        total=cp.total,
        portfolio=cp.portfolio,
        portfolio_name=settings.portfolio_name,
        period=settings.period,
        in_eur=settings.in_eur,
        risk_free=settings.risk_free,
        risk_profile=settings.risk_profile,
        advisor=advisor,
        names=cp.names,
        pos=cp.pos_table,
        pnl_totals=cp.pnl_totals,
        irr=cp.irr,
        stateful=True,
    )

    render_nav_and_dispatch(
        macro_labels, subnav, views, needs_portfolio, ctx, cp.compute_error, cp.notice
    )

    compliance_footer()


if __name__ == "__main__":
    main()
