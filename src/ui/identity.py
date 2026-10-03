"""Identità del consulente (tenant) per l'isolamento dei dati B2B.

Usa il login nativo di Streamlit (`st.user`/`st.login`, OIDC) quando è
configurato in produzione — vedi `[auth]` in `secrets.toml`. In locale, senza
configurazione, tutto ricade su un tenant di sviluppo così l'app resta usabile
senza attivare l'autenticazione.

ATTENZIONE: se l'OIDC non è configurato, l'isolamento per advisor NON è
garantito — ogni visitatore ricade sullo stesso tenant `DEV_ADVISOR`. È
responsabilità del deploy impostare `REQUIRE_AUTH=true` (vedi
`auth_required_but_missing`) per bloccare un ambiente pubblico senza auth.
"""

import os

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


def auth_required_but_missing() -> bool:
    """True se il deploy ha chiesto di imporre l'auth (`REQUIRE_AUTH=true`) ma
    l'OIDC non è configurato: in questo caso l'isolamento dati non è
    garantito e l'app non deve servire richieste."""
    required = os.getenv("REQUIRE_AUTH", "false").strip().lower() == "true"
    return required and not auth_configured()


def is_admin(advisor: str) -> bool:
    """True se `advisor` è nella allowlist admin (secrets `admin_emails`).

    Ruolo minimo oltre "advisor": accesso a statistiche cross-tenant e audit
    log, mai ai dati di portafoglio di altri consulenti.
    """
    try:
        admins = st.secrets.get("admin_emails", [])
    except Exception:
        admins = []
    return advisor.strip().lower() in {str(a).strip().lower() for a in admins}
