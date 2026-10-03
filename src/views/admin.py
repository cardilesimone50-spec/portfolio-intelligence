"""Vista Admin: statistiche cross-tenant e audit log — mai dati di portafoglio altrui."""

import streamlit as st

from src.data.store import platform_stats, recent_audit
from src.ui.components import sec
from src.ui.identity import auth_configured
from src.views.context import ViewContext


def render(ctx: ViewContext) -> None:
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
