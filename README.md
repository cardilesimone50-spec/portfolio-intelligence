# Portfolio Intelligence

Dashboard Python per l'analisi di portafogli azionari: rendimento/rischio in
euro (Sharpe, Sortino, max drawdown, VaR, beta/alpha vs Nasdaq-100),
correlazioni, fondamentali, ottimizzazione di Markowitz con frontiera
efficiente, backtest di strategie, alert automatici, report PDF, import
CSV/Excel dal broker, vista consulente multi-cliente e salvataggio
portafogli/storico analisi in SQLite.

I prezzi arrivano da una **catena di provider dati** con fallback
(`src/data/providers.py`): EODHD — dati con licenza commerciale, attivo con
`EODHD_API_KEY` — poi Yahoo Finance, poi Stooq. Pensata per sostituire la
sorgente senza toccare il resto del codice.

## Licenza

Elastic License 2.0 (source-available): puoi usare, modificare e ridistribuire
il software, ma **non offrirlo a terzi come servizio hosted/gestito** che ne
esponga le funzionalità principali. Vedi [LICENSE](LICENSE).

## Avvio

```bash
source venv/bin/activate
streamlit run app.py                              # dashboard web
python main.py -p AAPL:0.5 -p MSFT:0.5 --period 1y  # report CLI
python fundamentals_report.py AAPL MSFT NVDA      # fondamentali CLI
python download_nasdaq100.py                      # scarica/aggiorna il database prezzi
python -m pytest                                  # test
```

## Deploy

**Streamlit Community Cloud (gratuito):** vai su [share.streamlit.io](https://share.streamlit.io),
accedi con GitHub, "Create app" → repo `portfolio-intelligence`, branch `main`,
file `app.py`. Il database prezzi si scarica dal bottone in-app alla prima visita.

**Docker:**
```bash
docker build -t portfolio-intelligence .
docker run -p 8501:8501 portfolio-intelligence
```

**Database (Postgres in produzione):** lo schema è gestito con Alembic
(`alembic.ini` + `migrations/`), stessa risoluzione URL dell'app
(`DATABASE_URL`, altrimenti SQLite locale).
```bash
# database nuovo (vuoto): crea le tabelle
alembic upgrade head

# database esistente già in uso (creato da create_all prima di Alembic):
# segna lo schema attuale come aggiornato senza rieseguire le DDL
alembic stamp head
```

**Isolamento multi-tenant:** senza `[auth]` configurato nei secrets, ogni
visitatore condivide lo stesso tenant di sviluppo (nessun isolamento dati —
vedi `ROADMAP.md` §7). Per rifiutare l'avvio in assenza di auth, imposta
`REQUIRE_AUTH=true`. Per abilitare la vista admin (statistiche cross-tenant e
audit log), aggiungi `admin_emails = ["you@example.com"]` ai secrets.

## Struttura

```
src/
├── data/            accesso rete (yahoo_client), database SQLite (store), validazione
├── portfolio/       tipi base, rendimenti, rischio, ottimizzazione e frontiera efficiente
├── analytics/       performance: Sharpe, Sortino, drawdown, VaR, beta/alpha
├── fundamentals/    bilanci e multipli di valutazione
├── visualization/   grafici Altair riusabili
├── cli.py           parsing argomenti CLI
└── report.py        report testuale di portafoglio
```
