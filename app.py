"""Alias retrocompatibile: sceglie il profilo con APP_MODE=investor|advisor.

Storicamente `app.py` ERA l'unico entry point (quello che oggi è
`app_advisor.py`). Resta qui per non rompere deploy esistenti che puntano a
`streamlit run app.py` — su piattaforme dove si può impostare una variabile
d'ambiente ma non cambiare il comando di avvio, questo basta a scegliere il
profilo. Default "advisor": è il comportamento storico di questo file.

Se nessuno imposta APP_MODE, questo file deve restare quello che era: niente
sorprese per un deploy che faceva già `streamlit run app.py` senza secrets
OIDC configurati. Per questo, SOLO se il profilo è scelto esplicitamente,
app_advisor.py applica il suo default più severo (REQUIRE_AUTH=true); senza
APP_MODE il default è quello storico (REQUIRE_AUTH=false) — ma resta
sovrascrivibile da REQUIRE_AUTH nell'ambiente o da `require_auth` in
[auth] nei secrets (stessa precedenza di `resolve_require_auth`, riusata
qui apposta: un `require_auth = true` nei secrets deve valere anche per chi
lancia `app.py` senza scegliere un profilo).
Chi vuole il gate forzato senza toccare i secrets: `streamlit run
app_advisor.py` direttamente, o APP_MODE=advisor esplicito.

Avvio diretto per nome, più esplicito:
    streamlit run app_investor.py
    streamlit run app_advisor.py
"""

import os

from portfolio_intelligence.ui.identity import resolve_require_auth

_mode_chosen_explicitly = "APP_MODE" in os.environ
_MODE = os.getenv("APP_MODE", "advisor").strip().lower()

if not _mode_chosen_explicitly:
    resolve_require_auth(default_if_unset=False)

if _MODE == "investor":
    from app_investor import main
else:
    from app_advisor import main

main()
