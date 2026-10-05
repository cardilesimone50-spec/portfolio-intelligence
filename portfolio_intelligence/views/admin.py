"""Vista Admin: statistiche cross-tenant e audit log — mai dati di portafoglio altrui.

Il gate in app.py nasconde il tab "Admin" dalla nav per i non-admin, ma qui
c'è un controllo esplicito indipendente: `render` non deve fidarsi solo del
fatto di essere stata raggiunta dal dispatch della nav. Se in futuro qualcosa
chiama `render` per un altro percorso, questa riga resta l'ultima difesa.
"""

import streamlit as st

from portfolio_intelligence.data.store import platform_stats, recent_audit
from portfolio_intelligence.i18n import t
from portfolio_intelligence.ui.components import sec
from portfolio_intelligence.ui.identity import auth_configured, is_admin
from portfolio_intelligence.views.context import ViewContext


def render(ctx: ViewContext) -> None:
    if not is_admin(ctx.advisor):
        st.error(t("adm.denied"))
        st.stop()

    sec(t("adm.title"))
    st.caption(t("adm.caption"))

    if not auth_configured():
        st.warning(t("adm.no_auth"))

    stats = platform_stats()
    col1, col2, col3, col4 = st.columns(4)
    col1.metric(t("adm.advisors"), stats["advisors"])
    col2.metric(t("adm.portfolios"), stats["portfolios"])
    col3.metric(t("adm.analyses"), stats["analyses"])
    col4.metric(t("adm.last_sync"), stats["last_price_date"] or "n/a")

    sec(t("adm.activity"))
    audit = recent_audit(limit=50)
    if audit.empty:
        st.caption(t("adm.no_events"))
    else:
        st.dataframe(audit, width="stretch", hide_index=True)
