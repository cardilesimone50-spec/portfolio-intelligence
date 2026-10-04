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
APP_MODE la variabile resta quella storica (REQUIRE_AUTH=false, opt-in).
Chi vuole davvero il gate forzato: `streamlit run app_advisor.py` direttamente,
o APP_MODE=advisor esplicito.

Avvio diretto per nome, più esplicito:
    streamlit run app_investor.py
    streamlit run app_advisor.py
"""

import os

_mode_chosen_explicitly = "APP_MODE" in os.environ
_MODE = os.getenv("APP_MODE", "advisor").strip().lower()

if not _mode_chosen_explicitly:
    os.environ.setdefault("REQUIRE_AUTH", "false")

if _MODE == "investor":
    from app_investor import main
else:
    from app_advisor import main

main()
