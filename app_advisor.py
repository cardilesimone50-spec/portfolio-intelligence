"""Smarteefinance Advisor — Portfolio Intelligence professionale per il consulente B2B.

Avvio: streamlit run app_advisor.py

Stateful, multi-tenant, OIDC obbligatoria per impostazione predefinita (si
può disattivare solo esplicitamente con REQUIRE_AUTH=false nell'ambiente —
mai per difetto, un deploy pubblico senza auth non isola i dati). Portafogli,
analisi e audit log persistono sul DB (SQLite in locale, Postgres in
produzione via DATABASE_URL) isolati per `current_advisor()`.

Spazio di lavoro da consulente (views/advisor_workspace.py): book clienti
ordinato per priorità, scheda cliente con profilo di rischio salvato,
posizioni a lotti con IRR/XIRR reale, ottimizzazione di Markowitz, backtest
con costi di transazione, overlay di opzioni protettive e, per gli indirizzi
in `admin_emails`, statistiche cross-tenant e audit log.
"""

from portfolio_intelligence.router import bootstrap_page, init_session
from portfolio_intelligence.ui.identity import current_advisor
from portfolio_intelligence.views import advisor_workspace
from portfolio_intelligence.views.advisor_welcome import render_advisor_gate


def main() -> None:
    bootstrap_page("Smarteefinance Advisor | Professional Portfolio Intelligence", True)
    init_session()

    # consulente corrente (tenant): portafogli e analisi sono isolati per advisor
    advisor = current_advisor()

    # login istituzionale finché il consulente non è autenticato (st.stop() interno)
    render_advisor_gate(advisor)

    # spazio di lavoro del consulente: book clienti, scheda cliente, mercato, admin.
    # Interfaccia propria, non l'onboarding né la piattaforma dell'area Investor.
    advisor_workspace.render(advisor)


if __name__ == "__main__":
    main()
