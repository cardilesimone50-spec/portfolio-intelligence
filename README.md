# Portfolio Intelligence

Dashboard Python per l'analisi di portafogli azionari: rendimento/rischio in
euro (Sharpe, Sortino, max drawdown, VaR, beta/alpha vs Nasdaq-100),
correlazioni, fondamentali, ottimizzazione di Markowitz con frontiera
efficiente, backtest di strategie, alert automatici, report PDF, import
CSV/Excel dal broker, vista consulente multi-cliente e salvataggio
portafogli/storico analisi in SQLite.

I prezzi arrivano da una **catena di provider dati** con fallback
(`portfolio_intelligence/data/providers.py`): EODHD — dati con licenza commerciale, attivo con
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

## Autenticazione (OIDC)

L'app usa il login nativo di Streamlit (`st.login`/`st.user`). Senza un
provider configurato resta usabile ma **senza isolamento dati tra
utenti**. Per attivarlo con Google:

1. **Crea le credenziali OAuth** su [console.cloud.google.com](https://console.cloud.google.com):
   - Crea (o seleziona) un progetto.
   - *APIs & Services → OAuth consent screen*: tipo "External", nome app,
     email di supporto. Basta la versione minima, non serve pubblicarlo per
     uso interno/pochi utenti (restano in modalità "Testing": aggiungi le
     email degli advisor come "Test users").
   - *APIs & Services → Credentials → Create Credentials → OAuth client ID*,
     tipo "Web application".
   - **Authorized redirect URIs**: `http://localhost:8501/oauth2callback` in
     locale; in produzione aggiungi anche
     `https://<tuo-dominio>/oauth2callback` (es. `https://<app>.streamlit.app/oauth2callback`
     su Streamlit Community Cloud).
   - Copia **Client ID** e **Client secret**.

2. **Copia il template** `.streamlit/secrets.toml.example` →
   `.streamlit/secrets.toml` (ignorato da git) e incolla `client_id` e
   `client_secret`. Genera un `cookie_secret` tuo:
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

3. **Su Streamlit Community Cloud**: incolla lo stesso contenuto in
   *App settings → Secrets*, con `redirect_uri` aggiornato al dominio
   pubblico dell'app.

Una volta configurato, il banner "Auth not configured" in sidebar sparisce e
`current_advisor()` isola davvero i dati per email di chi ha fatto login.

## Struttura

Pacchetto Python installabile (`pip install -e .`), import stabili via
`portfolio_intelligence.*`:

```
portfolio_intelligence/
├── data/            accesso rete (yahoo_client), catena provider, database (store), validazione
├── portfolio/       tipi base, rendimenti, rischio, ottimizzazione e frontiera efficiente
├── analytics/       performance: Sharpe, Sortino, drawdown, VaR, beta/alpha, insight e alert
├── fundamentals/    bilanci e multipli di valutazione
├── visualization/   grafici Altair e report PDF
├── ui/              identità/auth, componenti e tema Streamlit
├── views/           una vista per sezione della dashboard (check-up, backtest, admin, ...)
├── config.py        costanti condivise (TRADING_DAYS, soglie di scoring, min_periods)
├── logging_config.py  logger strutturato condiviso
├── cli.py           parsing argomenti CLI
└── report.py        report testuale di portafoglio
```
