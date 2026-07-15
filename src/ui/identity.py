"""Identità del consulente (tenant) per l'isolamento dei dati B2B.

Usa il login nativo di Streamlit (`st.user`/`st.login`, OIDC) quando è
configurato in produzione — vedi `[auth]` in `secrets.toml`. In locale, senza
configurazione, tutto ricade su un tenant di sviluppo così l'app resta usabile
senza attivare l'autenticazione.
"""

import streamlit as st

DEV_ADVISOR = "local@dev"


def is_authenticated() -> bool:
    """True se un consulente ha effettuato il login (auth configurata e attiva)."""
    user = getattr(st, "user", None)
    try:
        return bool(user is not None and getattr(user, "is_logged_in", False))
    except Exception:
        return False


def current_advisor() -> str:
    """Email del consulente loggato, o il tenant di sviluppo in locale.

    È la chiave con cui portafogli e analisi vengono isolati per consulente.
    """
    if is_authenticated():
        email = getattr(st.user, "email", None)
        if email:
            return str(email)
    return DEV_ADVISOR


def auth_configured() -> bool:
    """True se l'autenticazione OIDC è configurata (secrets `[auth]` presenti)."""
    try:
        return "auth" in st.secrets
    except Exception:
        return False
