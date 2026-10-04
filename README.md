# Portfolio Intelligence

Motore di analisi di portafogli azionari — rendimento/rischio in euro
(Sharpe, Sortino, max drawdown, VaR, beta/alpha vs Nasdaq-100), correlazioni,
fondamentali, ottimizzazione di Markowitz, backtest di strategie, report PDF
— condiviso da **due prodotti Streamlit distinti**:

- **Smarteefinance Investor** (`app_investor.py`) — B2C, anonimo, stateless:
  check-up in 60 secondi, nessun login, nessun dato salvato da nessuna
  parte. Funnel ridotto: input → Health Score/problemi → metriche EUR → PDF.
- **Smarteefinance Advisor** (`app_advisor.py`) — B2B professionale: login
  OIDC, multi-cliente, portafogli a lotti con IRR reale, backtest con costi,
  overlay di opzioni protettive, audit log, vista Admin. Stateful su DB
  (SQLite in locale, Postgres in produzione), isolato per consulente.

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
streamlit run app_investor.py                       # Smarteefinance Investor (B2C, anonimo)
streamlit run app_advisor.py                         # Smarteefinance Advisor (B2B, login OIDC)
streamlit run app.py                                 # alias retrocompatibile → Advisor
APP_MODE=investor streamlit run app.py               # ...o Investor, via env var

python main.py -p AAPL:0.5 -p MSFT:0.5 --period 1y   # report CLI
python fundamentals_report.py AAPL MSFT NVDA         # fondamentali CLI
python download_nasdaq100.py                         # scarica/aggiorna il database prezzi
python -m pytest                                      # test
```

`app.py` esiste solo per non rompere deploy esistenti che puntano a
`streamlit run app.py` e non possono cambiare il comando di avvio ma possono
impostare una variabile d'ambiente: sceglie il profilo da `APP_MODE`
(default `advisor`, il comportamento storico di questo file). Per un deploy
nuovo, punta direttamente ad `app_investor.py` o `app_advisor.py`.

## Deploy

**Streamlit Community Cloud (gratuito):** vai su [share.streamlit.io](https://share.streamlit.io),
accedi con GitHub, "Create app" → repo `portfolio-intelligence`, branch `main`,
file `app_investor.py` o `app_advisor.py` (un'app Streamlit Cloud per
profilo, se vuoi offrirli entrambi come deploy separati). Il database prezzi
si scarica dal bottone in-app alla prima visita.

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
├── router.py        logica condivisa tra app_investor.py e app_advisor.py
├── cli.py           parsing argomenti CLI
└── report.py        report testuale di portafoglio
```

I tre entry point alla radice del repo: `app_investor.py`, `app_advisor.py`
(i due prodotti) e `app.py` (alias retrocompatibile, vedi "Avvio").
