"""Pagine legali (privacy, termini, cookie, note legali), footer e lingua del documento.

I testi stanno in `docs/legal/*.md` e usano segnaposto `{{campo}}` riempiti con
i dati societari dei secrets (`[legal]` in `.streamlit/secrets.toml`) o delle
variabili d'ambiente `LEGAL_<CAMPO>`. Un campo mancante resta visibile come
"[da completare: …]": meglio un buco evidente che un dato inventato.
"""

import os
import re
from pathlib import Path

import streamlit as st

from portfolio_intelligence.i18n import set_language, t

LEGAL_DIR = Path("docs/legal")

# chiave URL (?legal=...) → (chiave i18n del titolo, file)
DOCS = {
    "privacy": ("legal.privacy", "privacy.md"),
    "terms": ("legal.terms", "termini.md"),
    "cookies": ("legal.cookies", "cookie.md"),
    "imprint": ("legal.imprint", "note-legali.md"),
}

BUSINESS_FIELDS = {
    "name": "nome e cognome del titolare (o ragione sociale)",
    "email": "email di contatto per le richieste privacy",
    "address": "indirizzo o sede legale",
    "vat": "partita IVA",
    "rea": "numero REA",
    "pec": "PEC",
    "court": "foro competente per i rapporti tra professionisti",
    "hosting": "fornitore di hosting e paese",
    "audit_retention": "conservazione del registro di sicurezza",
    "updated": "data di ultimo aggiornamento",
}
# dati d'impresa: servono solo a chi ha un'attività economica (P.IVA, REA,
# PEC, foro B2B). Per un privato senza attività commerciale la riga che li
# contiene sparisce invece di mostrare un buco.
OPTIONAL_FIELDS = {"address", "vat", "rea", "pec", "court"}
DEFAULTS = {
    "hosting": "Streamlit Community Cloud, fornito da Snowflake Inc. (Stati Uniti)",
    "audit_retention": "Per il tempo necessario alle finalità di sicurezza",
    "updated": "5 ottobre 2026",
}


def business_details() -> dict[str, str]:
    """Dati del titolare: secrets `[legal]`, poi env `LEGAL_<CAMPO>`, poi i default.

    Un campo obbligatorio mancante resta visibile come "[da completare: …]":
    meglio un buco evidente che un dato inventato. I facoltativi restano vuoti.
    """
    try:
        configured = dict(st.secrets.get("legal", {}))
    except Exception:  # noqa: BLE001 — nessun secrets.toml in locale
        configured = {}
    details = {}
    for key, label in BUSINESS_FIELDS.items():
        value = configured.get(key) or os.getenv(f"LEGAL_{key.upper()}") or DEFAULTS.get(key)
        if value:
            details[key] = str(value)
        else:
            details[key] = "" if key in OPTIONAL_FIELDS else f"[da completare: {label}]"
    return details


def _is_configured(value: str) -> bool:
    return bool(value) and not value.startswith("[da completare")


def render_legal_doc(doc_key: str) -> str:
    _title_key, filename = DOCS[doc_key]
    text = (LEGAL_DIR / filename).read_text(encoding="utf-8")
    details = business_details()
    lines = [
        line
        for line in text.splitlines()
        if not any(details[field] == "" for field in re.findall(r"\{\{(\w+)\}\}", line))
    ]
    return re.sub(
        r"\{\{(\w+)\}\}", lambda m: details.get(m.group(1), m.group(0)), "\n".join(lines) + "\n"
    )


def render_legal_page_if_requested() -> None:
    """`?legal=privacy|terms|cookies|imprint` mostra il documento e ferma la pagina.

    Va chiamata prima di qualunque gate (login incluso): i documenti legali
    devono essere leggibili da chiunque, anche senza account.
    """
    doc_key = st.query_params.get("legal")
    if doc_key not in DOCS:
        return
    # la scheda nuova ha una sessione nuova: la lingua arriva dal link
    lang = "it" if st.query_params.get("lang") == "it" else "en"
    st.session_state.language = lang
    set_language(lang)
    sync_document_language(lang)
    st.markdown(
        '<div class="brand" style="margin:var(--s-2) 0 var(--s-5)">◆ SMARTEE<b>FINANCE</b></div>',
        unsafe_allow_html=True,
    )
    _l, body, _r = st.columns([1, 3, 1])
    with body:
        if lang != "it":
            st.caption(t("legal.italian_only"))
        st.markdown(render_legal_doc(doc_key))
        st.divider()
        legal_footer()
    st.stop()


def legal_footer() -> None:
    """Link ai documenti legali (in una nuova scheda: la sessione resta intatta)
    e dati identificativi del titolare, se configurati."""
    lang = st.session_state.get("language", "en")
    links = " · ".join(
        f'<a href="?legal={key}&lang={lang}" target="_blank" rel="noopener">{t(title_key)}</a>'
        for key, (title_key, _file) in DOCS.items()
    )
    details = business_details()
    labels = {"name": "{}", "address": "{}", "vat": "P.IVA {}"}
    identity = " · ".join(
        fmt.format(details[key]) for key, fmt in labels.items() if _is_configured(details[key])
    )
    st.markdown(
        f'<nav class="legal-footer" aria-label="{t("legal.nav_label")}">{links}'
        + (f"<div>{identity}</div>" if identity else "")
        + "</nav>",
        unsafe_allow_html=True,
    )


def sync_document_language(lang: str) -> None:
    """Allinea `<html lang>` alla lingua scelta (WCAG 3.1.1): Streamlit lo fissa a "en"."""
    safe = "it" if lang == "it" else "en"
    st.html(
        f'<script>document.documentElement.lang = "{safe}";</script>',
        unsafe_allow_javascript=True,
    )
