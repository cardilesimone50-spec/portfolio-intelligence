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
    """True se l'OIDC è configurato per davvero: serve un `client_id` dentro
    `[auth]`, non basta che la sezione esista. `[auth]` può contenere solo
    `require_auth` (vedi `resolve_require_auth`) senza alcuna credenziale —
    in quel caso l'OIDC NON è configurato, anche se "auth" compare in secrets.
    """
    try:
        return bool(st.secrets.get("auth", {}).get("client_id"))
    except Exception:
        return False


def resolve_require_auth(default_if_unset: bool) -> bool:
    """Decide se imporre l'auth, con questa precedenza:

    1. variabile d'ambiente REQUIRE_AUTH impostata dall'operatore (Docker,
       systemd, shell: vince sempre);
    2. `require_auth` dentro `[auth]` nei secrets (Streamlit Community Cloud,
       dove si impostano secrets dalla dashboard ma non variabili d'ambiente);
    3. `default_if_unset`, il default del profilo chiamante (investor=False,
       advisor=True).

    Sola lettura: non scrive nulla nell'ambiente. Investor e Advisor girano
    nello stesso processo (app.py): un valore scritto da una sessione
    deciderebbe il controllo per tutte le altre.
    """
    explicit = os.getenv("REQUIRE_AUTH")
    if explicit is not None:
        return explicit.strip().lower() == "true"
    try:
        secrets_auth = st.secrets.get("auth", {})
        if "require_auth" in secrets_auth:
            return bool(secrets_auth["require_auth"])
    except Exception:
        pass
    return default_if_unset


def auth_required_but_missing(required: bool | None = None) -> bool:
    """True se l'auth va imposta ma l'OIDC non è configurato: l'isolamento dati
    non è garantito e l'app non deve servire richieste.

    `required`: l'esito di `resolve_require_auth` per il profilo corrente;
    se assente si legge la sola variabile d'ambiente dell'operatore.
    """
    if required is None:
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
