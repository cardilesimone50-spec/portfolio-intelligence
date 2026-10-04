"""Router pubblico: due storie diverse, una scelta esplicita.

Senza APP_MODE impostato (il caso normale per il deploy pubblico), questo
file mostra una schermata di scelta — Investor (anonimo, immediato, nessuna
scrittura su DB) o Advisor (login OIDC, multi-tenant, nav completa) — invece
di saltare direttamente a un profilo. La scelta si ricorda nell'URL
(`?profile=investor|advisor`): bookmarkabile, sopravvive a un refresh, e
tornando sull'URL senza query string si torna alla schermata di scelta.

Cliccare "Sign in as Advisor" È una scelta esplicita tanto quanto impostare
APP_MODE=advisor: da qui in poi il profilo applica il suo default reale
(REQUIRE_AUTH=true per Advisor) senza reti di sicurezza — chi clicca quella
card si aspetta un vero login, non un bypass silenzioso.

APP_MODE=investor|advisor resta per deploy automatizzati che vogliono
saltare la schermata di scelta e andare dritti a un profilo (es. un
deployment interno pensato per essere solo-Advisor).

Avvio diretto per nome, senza passare da qui:
    streamlit run app_investor.py
    streamlit run app_advisor.py
"""

import os
from collections.abc import Callable

import streamlit as st

from portfolio_intelligence.i18n import set_language
from portfolio_intelligence.ui.components import render_profile_chooser
from portfolio_intelligence.ui.legal import DOCS as LEGAL_DOCS
from portfolio_intelligence.ui.legal import (
    legal_footer,
    render_legal_page_if_requested,
    sync_document_language,
)
from portfolio_intelligence.ui.theme import inject_theme
from portfolio_intelligence.views.common import language_selector

_MODE = os.getenv("APP_MODE", "").strip().lower()


def _go_investor() -> None:
    st.query_params["profile"] = "investor"


def _go_advisor() -> None:
    st.query_params["profile"] = "advisor"


if st.query_params.get("legal") in LEGAL_DOCS:
    # pagina legale aperta dal footer (nuova scheda): niente routing per profilo
    st.set_page_config(page_title="Smarteefinance | Legal", page_icon="◆", layout="wide")
    inject_theme()
    render_legal_page_if_requested()

profile = _MODE if _MODE in ("investor", "advisor") else st.query_params.get("profile")

run_app: Callable[[], None] | None
if profile == "investor":
    from app_investor import main as run_app
elif profile == "advisor":
    from app_advisor import main as run_app
else:
    run_app = None

if run_app is not None:
    run_app()
else:
    st.set_page_config(
        page_title="Smarteefinance | Choose your profile",
        page_icon="◆",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    inject_theme()
    set_language(st.session_state.get("language", "en"))
    sync_document_language(st.session_state.get("language", "en"))

    _spacer, lang_col = st.columns([6, 1])
    with lang_col:
        language_selector("lang_chooser")

    render_profile_chooser(on_investor=_go_investor, on_advisor=_go_advisor)
    legal_footer()
