"""Smarteefinance Investor — il check-up onesto del portafoglio in 60 secondi.

Avvio: streamlit run app_investor.py

Anonimo e stateless per design: nessun login, nessuna scrittura sul DB. I
dati che carichi (manuali, CSV/Excel) vivono solo in `st.session_state` per
la durata della sessione e spariscono alla chiusura — niente da cancellare
perché non è mai stato salvato da nessuna parte.

Funnel ridotto al check-up: input rapido → Health Score / problemi e
opportunità → metriche in euro con rischio cambio → report PDF scaricabile.
Niente dashboard clienti, niente vista Admin, niente power feature da
consulente (opzioni protettive, backtest multi-strategia): quelle restano in
Smarteefinance Advisor (`app_advisor.py`).
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
from portfolio_intelligence.ui.identity import current_advisor
from portfolio_intelligence.views import checkup as checkup_view
from portfolio_intelligence.views import correlations, fundamentals, gate, market, metrics, visual
from portfolio_intelligence.views.context import ViewContext
from portfolio_intelligence.views.sidebar import render_sidebar


def main() -> None:
    bootstrap_page("Smarteefinance Investor | Portfolio Check-up", False)
    init_session()

    # ================================================================ ONBOARDING GATE
    gate.render_gate()  # se il gate è attivo, disegna lo stage e chiama st.stop()

    # nessuna identità reale: senza OIDC current_advisor() torna sempre il
    # tenant di sviluppo — qui serve solo come valore segnaposto per
    # ViewContext.advisor (checkup.py lo usa solo per NON stampare un nome
    # advisor nel PDF, cosa che vogliamo comunque in modalità anonima)
    advisor = current_advisor()
    settings = render_sidebar(advisor, advisor_mode=False)

    positions = normalize_portfolio(st.session_state.positions)
    cp = compute_portfolio(positions, settings)

    render_header(settings.in_eur, "Investor")
    st.info(t("investor.disclaimer"), icon="ℹ️")

    # nav ridotta al funnel retail: niente Strategies (opzioni/backtest),
    # niente Clients, niente Admin — quelle sono power feature B2B
    macro_labels = {
        "Check-up": t("nav.checkup"),
        "Analysis": t("nav.analysis"),
        "Market": t("nav.market"),
    }
    subnav = {
        "Analysis": [(t("nav.metrics"), "Analisi"), (t("nav.charts"), "Visual")],
        "Market": [
            (t("nav.nasdaq"), "Mercato"),
            (t("nav.correlations"), "Correlazioni"),
            (t("nav.fundamentals"), "Fondamentali"),
        ],
    }
    views = {
        "Check-up": checkup_view.render,
        "Analisi": metrics.render,
        "Visual": visual.render,
        "Mercato": market.render,
        "Correlazioni": correlations.render,
        "Fondamentali": fundamentals.render,
    }
    needs_portfolio = {"Check-up", "Analisi", "Visual"}

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
        stateful=False,
    )

    render_nav_and_dispatch(macro_labels, subnav, views, needs_portfolio, ctx, cp.compute_error)

    compliance_footer()


if __name__ == "__main__":
    main()
