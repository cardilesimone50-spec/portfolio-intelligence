"""Alias retrocompatibile: sceglie il profilo con APP_MODE=investor|advisor.

Storicamente `app.py` ERA l'unico entry point (quello che oggi è
`app_advisor.py`). Resta qui per non rompere deploy esistenti che puntano a
`streamlit run app.py` — su piattaforme dove si può impostare una variabile
d'ambiente ma non cambiare il comando di avvio, questo basta a scegliere il
profilo. Default "advisor": è il comportamento storico di questo file.

Avvio diretto per nome, più esplicito:
    streamlit run app_investor.py
    streamlit run app_advisor.py
"""

import os

_MODE = os.getenv("APP_MODE", "advisor").strip().lower()

if _MODE == "investor":
    from app_investor import main
else:
    from app_advisor import main

main()
