"""Vista Admin: statistiche cross-tenant e audit log — mai dati di portafoglio altrui.

Il gate in app.py nasconde il tab "Admin" dalla nav per i non-admin, ma qui
c'è un controllo esplicito indipendente: `render` non deve fidarsi solo del
fatto di essere stata raggiunta dal dispatch della nav. Se in futuro qualcosa
chiama `render` per un altro percorso, questa riga resta l'ultima difesa.
"""

import streamlit as st

from portfolio_intelligence.data.store import platform_stats, recent_audit
from portfolio_intelligence.ui.components import sec
from portfolio_intelligence.ui.identity import auth_configured, is_admin
from portfolio_intelligence.views.context import ViewContext


def render(ctx: ViewContext) -> None:
    if not is_admin(ctx.advisor):
        st.error("Access denied: this section is for admins only.")
        st.stop()

    sec("Platform — admin only")
    st.caption(
        "Cross-tenant counters and the audit log. Never shows another "
        "advisor's portfolio contents — only who did what, and when."
    )

    if not auth_configured():
        st.warning(
            "⚠️ OIDC auth is not configured: tenant isolation is not "
            "guaranteed. These counters may be meaningless if every "
            "visitor shares the same dev tenant."
        )

    stats = platform_stats()
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Advisors", stats["advisors"])
    col2.metric("Saved portfolios", stats["portfolios"])
    col3.metric("Analyses logged", stats["analyses"])
    col4.metric("Last price sync", stats["last_price_date"] or "—")

    sec("Recent activity (all tenants)")
    audit = recent_audit(limit=50)
    if audit.empty:
        st.caption("No audit events yet.")
    else:
        st.dataframe(audit, width="stretch", hide_index=True)
