"""Selettore d'area Investor | Advisor, visibile in entrambe le aree.

Cambia area nella stessa sessione (query param `profile` letto dal router di
app.py), senza ricaricare la pagina. Ogni area tiene il proprio portafoglio di
lavoro: passando da un cliente Advisor all'area Investor e ritorno, nessuna
delle due perde o eredita le posizioni dell'altra.

Compare solo quando l'app gira dietro il router (`app.py` imposta
`area_router`): lanciando direttamente app_investor.py o app_advisor.py, o con
APP_MODE fisso, non c'è un'altra area verso cui andare.
"""

import streamlit as st

from portfolio_intelligence.i18n import t

AREAS = ("investor", "advisor")
ROUTER_FLAG = "area_router"


def _switch(current: str, key: str) -> None:
    target = st.session_state.get(key)
    if target not in AREAS or target == current:
        st.session_state[key] = current  # un secondo clic sull'area attiva non la deseleziona
        return
    st.session_state[f"area_positions_{current}"] = st.session_state.get("positions", {})
    st.session_state.positions = st.session_state.get(f"area_positions_{target}", {})
    st.query_params["profile"] = target


def area_switch(current: str, key: str) -> None:
    """Disegna il selettore; `key` distingue le posizioni (intestazione, sidebar…)."""
    if not st.session_state.get(ROUTER_FLAG):
        return
    st.segmented_control(
        t("area.label"),
        AREAS,
        default=current,
        format_func=lambda area: t(f"area.{area}"),
        key=key,
        on_change=_switch,
        args=(current, key),
        label_visibility="collapsed",
        width="stretch",
    )
