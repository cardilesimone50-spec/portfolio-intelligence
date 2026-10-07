# ROADMAP — Portfolio Intelligence

> Obiettivo: diventare il miglior software open-source di Portfolio Intelligence.
> Documento di lavoro del CTO — aggiornato al 2026-10-04.

## MVP — "Il check-up onesto in 60 secondi per l'investitore europeo"

**Proposta di valore**: carichi il portafoglio (editor, CSV o Excel) e in meno di
un minuto ottieni uno score di salute, i problemi concreti, il rischio misurato
**in euro cambio incluso** e un report PDF condivisibile. La parola chiave è
*onesto*: rendimento composto (non medie gonfiate), rischio cambio incluso,
limiti di ogni stima dichiarati.

**Differenziatore**: quasi nessun tool retail misura il rischio in EUR per
l'investitore europeo — su titoli USA il cambio EUR/USD può dominare il
risultato e gli altri lo ignorano.

**Nel funnel MVP**: input rapido → check-up (score/problemi/opportunità) →
metriche EUR → report PDF.
**Power features fuori dal funnel** (restano ma non sono l'MVP): backtest,
galassia, Markowitz, correlazioni Nasdaq-100.

**Metrica north-star**: tempo dal primo avvio al primo report generato < 60s.

Stato: ✅ Elastic License 2.0 (source-available, non MIT come pianificato — vedi
nota in P0-1) · ✅ conversione EUR con rischio cambio (toggle, default ON) ·
✅ rendimento annualizzato composto · ✅ risk-free configurabile per Sharpe/Sortino
· ✅ import Fineco + risoluzione ISIN→ticker (OpenFIGI) · ✅ deploy pubblico
(Dockerfile + guida Streamlit Cloud in README). Il funnel MVP originale è
completo; il prodotto è andato oltre: posizioni a lotti con data d'acquisto e
IRR vero, overlay di opzioni protettive con catene reali, onboarding a gate,
identità consulente multi-tenant (B2B).

---

## Stato attuale

- ~9.500 righe Python; pacchetto installabile `portfolio_intelligence/` su
  `data / portfolio / analytics / fundamentals / ui / views / visualization`
  + `router.py` (logica condivisa di bootstrap/pipeline/nav). **Due prodotti
  Streamlit distinti** (2026-10-04) sullo stesso motore: `app_investor.py`
  (B2C, anonimo, stateless — niente login, niente scrittura su DB, nav
  ridotta al check-up) e `app_advisor.py` (B2B, OIDC obbligatoria di default,
  multi-tenant, nav completa inclusa vista Admin). `app.py` è ora il router
  pubblico: senza `APP_MODE` mostra una schermata di scelta a due card
  ("Due storie diverse", bilingue EN/IT) invece di saltare direttamente ad
  Advisor; la scelta vive in `?profile=investor|advisor` nell'URL
  (bookmarkabile, sopravvive al refresh). `APP_MODE` resta per deploy
  automatizzati che vogliono saltare la schermata. `app_advisor.py` apre ora
  su una console istituzionale dedicata (`advisor_welcome.py`): login SSO con
  header enterprise e badge di fiducia se non autenticato, welcome workspace
  con KPI reali (portafogli salvati, ultimo check-up, stato feed prezzi) e
  tre quick action se autenticato — mostrata una sola volta per sessione.
  262 test verdi, coverage
  86% con soglia all'80%, mypy pulito, CI GitHub Actions (ruff lint+format,
  mypy, coverage, matrice Python 3.11/3.12/3.13).
- Dati: catena di provider con fallback (`portfolio_intelligence/data/providers.py`) — EODHD (se
  configurata `EODHD_API_KEY`) → Yahoo chart diretto → yfinance → Stooq;
  storico Nasdaq-100 in SQLite/Postgres (~122k righe) con merge incrementale.
- Funzionalità MVP: onboarding a gate (landing → ticker → loading), check-up
  con score, metriche di rischio (Sharpe, Sortino, VaR, drawdown, beta/alpha)
  in EUR, correlazioni, Markowitz + frontiera, backtest con costi di
  transazione, report PDF con grafici vettoriali, import CSV/Excel/Fineco con
  risoluzione ISIN→ticker, i18n EN/IT.
- Oltre l'MVP: posizioni a lotti con data d'acquisto e IRR vero (XIRR), overlay
  di opzioni protettive con catene reali (non solo stimate) e tabelle di
  confronto contratti, identità consulente multi-tenant (isolamento dati per
  advisor, pronta per login OIDC nativo di Streamlit).

---

## 1. Problemi (in ordine di priorità)

### P0 — Bloccanti per l'obiettivo open-source

| # | Problema | Dettaglio | Stato |
|---|----------|-----------|-------|
| 1 | **Nessuna LICENSE** | Senza licenza il codice non è open source: nessuno può legalmente usarlo o contribuire. Scegliere MIT (adozione massima) o AGPL (protegge da SaaS chiusi). | ✅ Risolto — ma con **Elastic License 2.0** (source-available), non MIT: vieta a terzi di offrire il software come servizio hosted/gestito. Coerente col pivot B2B, ma è una scelta diversa da quella pianificata qui — da tenere a mente se l'obiettivo "open-source" in cima al documento resta invariato |
| 2 | **Rischio cambio ignorato** | Gli importi sono in EUR ma i prezzi in USD. Rendimenti e VaR "in euro" ignorano l'EUR/USD: per un investitore europeo su titoli USA il cambio può dominare il risultato. Serve la serie EURUSD=X e la conversione delle equity curve. | ✅ Risolto |
| 3 | **Annualizzazione aritmetica** | "Guadagno atteso = media giornaliera × 252" sovrastima sistematicamente rispetto al rendimento composto (CAGR), proprio il numero mostrato più in grande a un utente retail. Passare al geometrico o etichettare onestamente. | ✅ Risolto |
| 4 | **Fonte dati unica e fragile** | yfinance usa API non ufficiali Yahoo: rate-limit, cambi di schema improvvisi, nessuna garanzia. Serve un layer provider astratto + almeno un fallback (es. Stooq per i prezzi) e retry/backoff. | ✅ Risolto — catena EODHD → Yahoo chart diretto → yfinance → Stooq (`portfolio_intelligence/data/providers.py`) |

### P1 — Correttezza e affidabilità

| # | Problema | Dettaglio | Stato |
|---|----------|-----------|-------|
| 5 | **Risk-free = 0** | Sharpe/Sortino calcolati con tasso zero in un mondo a tassi positivi: sovrastimati. Prendere il T-bill 3M (^IRX) come default. | ✅ Risolto |
| 6 | **Survivorship bias nel backtest** | L'universo usa i componenti *attuali* del Nasdaq-100: le strategie (soprattutto momentum) risultano gonfiate. Serve lo storico dei constituent (dataset pubblici o snapshot periodici nel DB). | ⬜ Aperto — dichiarato onestamente in UI (`portfolio_intelligence/views/backtest.py`), ma non ancora risolto |
| 7 | **Backtest senza costi** | Nessun costo di transazione/slippage: il momentum trimestrale su 10 titoli ruota molto e in realtà renderebbe meno. Aggiungere bps configurabili per ribilanciamento. | ✅ Risolto — `cost_bps` configurabile in `portfolio_intelligence/analytics/backtest.py` |
| 8 | **Import Fineco/ISIN irrisolto** | L'importer generico gestisce sinonimi e preamboli ma senza file reali dei broker non è garantito. Manca la risoluzione ISIN→ticker (OpenFIGI API, gratuita) e il suffisso di mercato (.MI, .DE) per i titoli non-USA. | ✅ Risolto — parsing Fineco + `resolve_isins` via OpenFIGI (`portfolio_intelligence/data/isin.py`) |
| 9 | **`Ticker.info` sequenziale** | I fondamentali fanno 1 richiesta HTTP per ticker in loop: 10 titoli = ~10s. Parallelizzare (ThreadPool) e cachare su disco con TTL. | ✅ Risolto — `ThreadPoolExecutor` in `portfolio_intelligence/fundamentals/valuation.py` |
| 10 | **Nessun logging** | Solo `print` negli script; in caso di errore dati non c'è traccia diagnostica. Introdurre `logging` strutturato. | ✅ Risolto (2026-10-04) — `portfolio_intelligence/logging_config.py`, cablato su `ProviderChain.fetch` (warning sui fallback, error se tutti i provider falliscono). I `print()` nei CLI (`main.py`, `fundamentals_report.py`, ecc.) restano: sono l'output del tool, non diagnostica |

### P2 — Architettura e manutenzione

| # | Problema | Dettaglio | Stato |
|---|----------|-----------|-------|
| 11 | **app.py monolite (857 righe)** | Tutte le 6 tab in un file: UI non testabile, merge conflict garantiti appena si è in due. Spacchettare in `portfolio_intelligence/ui/` (una view per tab) + testare con `streamlit.testing.AppTest`. | ✅ Risolto — `app.py` ora 224 righe (solo router), viste in `portfolio_intelligence/views/` |
| 12 | **Accoppiamento implicito tra tab** | Le tab condividono variabili globali di script (`amounts`, `computed`): l'ordine dei blocchi è vincolante e fragile. Servono uno stato applicativo esplicito (dataclass in `st.session_state`). | ✅ Risolto — `ViewContext` dataclass esplicita (`portfolio_intelligence/views/context.py`) |
| 13 | **Packaging non standard** | Import `from src.x import y`: non installabile via pip, il nome `src` è generico. Migrare a `pyproject.toml` con package `portfolio_intelligence`, entry point CLI. | ✅ Risolto (2026-10-04) — cartella rinominata `src/` → `portfolio_intelligence/` (rename git, history preservata), tutti gli import aggiornati (import statement, monkeypatch a stringa nei test, docstring). Aggiunto `[build-system]` (mancava del tutto: `pip install -e .` non avrebbe funzionato) con `setuptools`; `[tool.setuptools.packages.find]` punta a `portfolio_intelligence*`. Verificato `pip install -e .` da una directory esterna al repo |
| 14 | **Costanti duplicate** | `TRADING_DAYS = 252` definito in 5 moduli; euristica `min_periods` copiata in più punti; soglie degli score sparse. Centralizzare in `config.py`. | ✅ Risolto (2026-10-04) — `portfolio_intelligence/config.py` ora è l'unica fonte per: `TRADING_DAYS`; l'euristica `min_periods` (funzione `rolling_min_periods`, duplicata identica in pipeline/clients/correlations + il default statico in `risk.py`); le bande di Sharpe/Sortino/drawdown/beta/correlazione (`interpret.py`); le soglie di scoring/DNA/radar/health (`insights.py`, `alerts.py`); le bande colore dell'Health Score (duplicate in 4 punti: UI, PDF ×2, book clienti) |
| 15 | **DB senza migrazioni né manutenzione** | Schema creato ad-hoc in `_connect`; `load_prices()` pivota tutto in memoria a ogni chiamata (nessuna query per range di date); tabella `analyses` a crescita illimitata. | ✅ Risolto per la parte migrazioni — Alembic (`migrations/`), verificato in CI (`alembic upgrade head`); `load_prices()` pivota ancora tutto in memoria, resta aperto |
| 16 | **CI minima** | Solo pytest su un solo Python. Aggiungere ruff (lint+format), mypy, coverage con soglia, matrice 3.11/3.12/3.13. | ✅ Risolto (2026-10-04) — mypy pulito su tutto il pacchetto (0 errori, 63 file: 150 errori iniziali in `views/` chiusi con `assert` che documentano l'invariante "dispatchata solo con portafoglio calcolato" invece di sopprimerli, pochi `# type: ignore` mirati sui veri limiti degli stub Altair/Streamlit); coverage con soglia 80% (`pytest-cov`, config in `pyproject.toml`, reale: 86%) scoped sull'engine (`data/portfolio/analytics/fundamentals`) — `views/ui/visualization/charts.py` esclusi dal gate perché sono superficie di rendering Streamlit non unit-testabile senza `AppTest` (dichiarato in un commento nel config, non nascosto); matrice Python 3.11/3.12/3.13 in CI, installa via `pip install -e ".[dev]"` invece dei pin esatti di requirements.txt (pensati per il deploy, non per testare più versioni) |

### P3 — Esperienza e portata

| # | Problema | Dettaglio | Stato |
|---|----------|-----------|-------|
| 17 | **Solo italiano, stringhe hardcoded** | Per un progetto open-source internazionale serve i18n (EN default, IT) con catalogo messaggi. | ✅ Risolto — i18n EN/IT (`portfolio_intelligence/i18n.py`) |
| 18 | **Universo solo Nasdaq-100** | S&P 500, STOXX 600, FTSE MIB, watchlist custom. | 🟡 Parziale — benchmark total return per cliente (ETF: QQQ, SPY, CSMIB, EXSA) con storico nel DB e tabella dei componenti (`portfolio_intelligence/data/benchmarks.py`); restano gli universi di titoli per Mercato/backtest e le watchlist |
| 19 | **PDF senza grafici** | Il report è solo testo/tabelle: aggiungere chart (matplotlib → immagine embedded). | ✅ Risolto — grafici vettoriali nel report (`portfolio_intelligence/visualization/pdf_report.py`) |
| 20 | **Nessuna storia di deploy** | Niente Dockerfile, niente guida Streamlit Cloud, secrets non gestiti. | ✅ Risolto — Dockerfile + guida Streamlit Cloud in README, bridge `DATABASE_URL` da secrets |

---

## 2. Debito tecnico

- [ ] `save_prices`: `PerformanceWarning` per DataFrame frammentato (copy prima del melt) — non riverificato.
- [x] `load_market_db()` non è cachato → risolto, `@st.cache_data` pervasivo in `portfolio_intelligence/views/common.py` (prezzi, fondamentali, EUR/USD, prezzo storico).
- [x] Session state del `data_editor` perso a ogni reload → **obsoleto**: il flusso di inserimento posizioni è stato riscritto (gate a 3 stadi con `selectbox`/`number_input`), il vecchio `data_editor` non esiste più.
- [x] `fundamentals_report.py` e `analyze_nasdaq100.py` duplicano logica dell'app → ridimensionati (62 e 34 righe), vicini a thin wrapper dell'engine.
- [ ] Indice temporale naive (no timezone): esplicitare UTC — non riverificato.
- [x] Validazione input dal DB assente → risolto (2026-10-04): `validate_price_rows` scarta righe `prices` con data/prezzo corrotti prima del pivot, `safe_load_positions` scarta un portafoglio con JSON corrotto invece di far crashare l'intero book — entrambe loggano cosa scartano.
- [ ] Cartella `data/` contiene ancora i CSV legacy (`nasdaq100_prices.csv`, `nasdaq100_returns.csv`) accanto al DB: rimuovere il fallback CSV dopo un periodo di grazia.

---

## 3. Miglioramenti a funzionalità esistenti

1. **Backtest**: ✅ costi di transazione (`cost_bps`) già fatti — restano ribilanciamento configurabile (mensile/trimestrale/annuale), metriche per strategia (Sharpe, max DD, turnover), walk-forward.
2. **Ottimizzazione**: vincoli utente (peso max per titolo/settore), shrinkage della covarianza (Ledoit-Wolf), Black-Litterman come opzione avanzata — ancora da fare.
3. **VaR**: aggiungere CVaR (expected shortfall) e VaR parametrico accanto allo storico; orizzonti multipli — ancora da fare.
4. **Score/DNA**: percentili rispetto all'universo invece di soglie assolute (più robusti tra settori); documentare la metodologia in `docs/METHODOLOGY.md` — ancora da fare.
5. **Alert**: canale push reale — script `check_alerts.py` schedulabile via cron + notifica Telegram/email (richiede credenziali utente) — ancora da fare.
6. **Galaxy/Radar**: legenda interattiva, drill-down sul titolo cliccato — vista presente (`portfolio_intelligence/views/visual.py`), interattività ancora da fare.

---

## 4. Nuove funzionalità

### Spedite (non previste nella versione originale di questo documento)

| Feature | Note |
|---|---|
| **Posizioni a lotti con data d'acquisto** | IRR vero (XIRR) al posto del rendimento stimato, prezzo auto-compilato dallo storico alla data del lotto. |
| **Overlay di opzioni protettive** | Catene reali (non solo stimate) con tabelle di confronto contratti, side by side. |
| **Onboarding a gate** | Landing → ticker → loading, piattaforma bloccata finché non c'è un portafoglio. |
| **Identità consulente multi-tenant (B2B)** | Isolamento dati per advisor, pronto per login OIDC nativo Streamlit. |
| **Supporto multi-valuta (EUR/USD)** | Risolveva anche P0-2, ora chiuso. |
| **Risoluzione ISIN → ticker** | Via OpenFIGI, chiudeva P1-8. |
| **Deploy pubblico** | Dockerfile + guida Streamlit Cloud, chiudeva P3-20. |
| **Monte Carlo (area Advisor)** | ✅ Operativo (2026-10-05). `analytics/monte_carlo.py`: bootstrap storico a blocchi e GBM parametrico, seed fisso, percentili p5-p95 mese per mese, probabilità di perdita, VaR al 95%, CAGR per percentile. Fan chart Altair nella scheda cliente (Strategie → Monte Carlo) e tabella p10/p50/p90 a 1-3-5 anni nel PDF Advisor. Escluso dall'area Investor, che dichiara di non fare previsioni. Test: `tests/test_monte_carlo.py`. |

### Ancora da fare (ordinate per rapporto valore/sforzo)

| Priorità | Feature | Note |
|----------|---------|------|
| Media | **Universi aggiuntivi** | Benchmark total return per cliente fatto (ETF SPY, CSMIB ed EXSA). Resta: componenti di S&P 500/FTSE MIB in `benchmark_constituents` (lista Wikipedia stabile) per Mercato e backtest, indici total return veri (S&P 500, FTSE MIB, STOXX 600) al posto degli ETF se un fornitore con licenza li pubblica, watchlist custom salvate nel DB. |
| Media | **Factor analysis reale** | `portfolio_intelligence/analytics/factors.py` oggi calcola solo i fattori per lo stock-picking del backtest (momentum, low-vol, trend); manca la regressione dei rendimenti del portafoglio su fattori di mercato. |
| Media | **Export Excel** | Il gemello del PDF per chi lavora in spreadsheet. |
| Bassa | **API REST (FastAPI)** | Separa engine e UI; abilita app mobile/terze parti. Solo dopo aver chiuso il packaging (P2-13, ancora parziale). |
| Bassa | **PyPI** | Pubblicare l'engine come libreria `portfolio-intelligence`. |

---

## 5. Piano di rilascio proposto

### v0.2 — "Open Source Ready" 🟡 parziale
✅ LICENSE (Elastic License 2.0, non MIT) · ✅ README con guida deploy ·
✅ pyproject.toml (con `[build-system]`, installabile via `pip install -e .`) ·
✅ spacchettamento app.py · ✅ rinomina package `src` → `portfolio_intelligence` ·
✅ mypy+coverage+matrice Python in CI · ✅ logging strutturato — resta:
CONTRIBUTING.md.

### v0.3 — "Numeri onesti" ✅ fatto
Multi-valuta EUR/USD · rendimento geometrico · risk-free reale · costi nel
backtest · provider dati astratto con fallback e retry · fondamentali
paralleli con cache — manca solo il CVaR (resta in §3).

### v0.4 — "Import per tutti" 🟡 parziale
✅ OpenFIGI ISIN→ticker · ✅ parser Fineco su file reali — restano: suffissi di
mercato (.MI, .DE) per i titoli non-USA, universi S&P 500 e FTSE MIB.

### v1.0 — "Prodotto" 🟡 parziale
✅ Deploy pubblico (Docker + Streamlit Cloud) · ✅ i18n EN/IT · ✅ identità
consulente multi-tenant (base per l'auth, non ancora login OIDC attivo in
produzione) · ✅ Monte Carlo (area Advisor) — restano: alert Telegram/email
schedulati, factor analysis, storico constituent per backtest senza
survivorship bias.

### v1.1 — non pianificata in origine, emersa dallo sviluppo reale
Posizioni a lotti con IRR vero · overlay di opzioni protettive con catene
reali e confronto contratti · onboarding a gate. Già spedite (§4).

---

## 6. Architettura target vs attuale

> Proposta di stack a 10 layer valutata il 2026-10-04 (fonte: diagramma esterno,
> tipico di una piattaforma dati/AI multi-sorgente ed event-driven). Confronto
> con lo stato attuale (monolite Streamlit, SQLAlchemy su SQLite/Postgres,
> cache in-process, script batch) per capire cosa adottare e quando.

| # | Layer proposto | Stato reale | Valutazione |
|---|---|---|---|
| 01 | Fonti dati API (webhook/CSV/DB) | Yahoo Finance (yfinance) + import CSV/Excel già presenti | ✅ Già c'è, nessun webhook necessario oggi |
| 02 | Ingestion/ETL (Airbyte/Singer) | Script Python ad-hoc (`download_nasdaq100.py`) | ❌ Overkill: 1-2 fonti non giustificano lo stack operativo di Airbyte |
| 03 | Message broker (RabbitMQ/Kafka) | — | ❌ Non necessario: nessun servizio disaccoppiato che produce/consuma eventi, tutto è request/response sincrono in un singolo processo |
| 04 | PostgreSQL + TimescaleDB | Postgres già supportato via `DATABASE_URL` (`portfolio_intelligence/data/store.py`) | 🟡 Parziale: hypertable utile solo quando le query per range di date su `prices` diventano un collo di bottiglia (oggi 122k righe sono banali) |
| 05 | Cache semantica (Redis) | `@st.cache_data` in-process | ❌ Prematuro: serve con più istanze dell'app o con un vero layer LLM (cache di embedding/risposte), nessuno dei due casi esiste oggi |
| 06 | Logic Engine (Pandas/scikit-learn) | `portfolio_intelligence/analytics`, `portfolio_intelligence/portfolio`, `portfolio_intelligence/fundamentals` | ✅ Già il cuore del progetto |
| 07 | Vector DB/RAG (Qdrant/ChromaDB) | — | ❌ Fuori roadmap: ha senso solo se nasce una feature "chat col portafoglio" |
| 08 | IA/LLM locale (Ollama) | — | ❌ Nuova direzione di prodotto, non un layer da aggiungere di striscio: richiede sizing, prompt engineering, eval — scope a sé |
| 09 | Orchestrazione (n8n/Airflow) | Script manuali | ❌ Overkill per 1-2 job schedulati: basta cron o GitHub Actions; rivalutare quando le automazioni reali (es. alert §3-5) superano 3-4 |
| 10 | UI (Streamlit/Superset) | Streamlit | ✅ Scelta corretta: prodotto guidato con gate di onboarding, viste custom e logica di business — Superset è per BI esplorativa su un warehouse, non sostituisce questo |

**Lettura**: lo stack proposto è quello di una piattaforma dati/AI multi-sorgente
ed event-driven con assistente conversazionale. Il prodotto attuale è
single-tenant-per-advisor, con flusso guidato e output deterministici (niente
LLM, niente eventi asincroni). 6 layer su 10 (02, 03, 05, 07, 08, 09) risolvono
problemi che questo codebase non ha ancora — non vanno scartati, ma adottati
solo quando compare il trigger concreto che li giustifica.

**Percorso incrementale** (coerente col piano di rilascio in §5):

1. Restare su Postgres semplice; valutare TimescaleDB solo quando il backtest
   a storico esteso (constituent storici, P1-6) rende lente le query per range.
2. Per gli alert schedulati (v1.0) partire da cron/GitHub Actions; passare a
   n8n solo se le automazioni diventano >3-4 e serve visibilità visuale.
3. RAG/LLM locale (Qdrant/Chroma + Ollama) solo a fronte di una decisione
   esplicita di aggiungere un assistente AI sul portafoglio — nuova iniziativa
   di prodotto, non un layer infrastrutturale isolato.
4. Redis e message broker: aspettare un trigger concreto (scaling multi-istanza
   dell'app, o servizi realmente disaccoppiati tra loro).

---

## 7. Capacità attuale: chi possiamo servire oggi

> Documentato il 2026-10-04, prima del prossimo pitch commerciale. Lo stack
> bundlato (Streamlit + SQLite/Postgres singolo + cache in-process, vedi §6)
> non è sbagliato: è la base giusta per i primi clienti. Non è pronto per un
> cliente enterprise — e questo va dichiarato prima di promettere il contrario.

| Dimensione | Realtà oggi | Soglia enterprise | Gap |
|---|---|---|---|
| **Isolamento multi-tenant** | ✅ Risolto in parte, ora **testato** (2026-10-04): `REQUIRE_AUTH=true` fa rifiutare l'avvio se l'OIDC non è configurato (`auth_required_but_missing`, `app.py`), con un test di regressione che verifica l'ordine nel sorgente (il gate deve stare prima di sidebar/piattaforma, non solo esistere); senza quel flag, un banner visibile avvisa che l'isolamento non è garantito. `portfolio_intelligence/data/store.py` filtra ogni query (`list_portfolios`, `save_portfolio`, `delete_portfolio`, `load_analyses`) su `advisor` via chiave composta (advisor, name): un advisor non può leggere, sovrascrivere o cancellare i dati di un altro nemmeno conoscendone il nome esatto. La vista Admin ora ha un controllo `is_admin()` esplicito dentro `admin.render()` (non si fida solo del tab nascosto in nav) e blocca prima di toccare dati cross-tenant. Copertura: `tests/test_tenant_isolation.py`, 13 test | SSO/OIDC obbligatorio by default in produzione, non opt-in via env var | 🟡 Il gate esiste e ora è testato, ma resta opt-in nel deploy |
| **Scalabilità del processo** | Un solo processo Streamlit (`streamlit run app.py`), nessun `docker-compose`, nessun orchestratore multi-replica; stato di sessione e cache (`@st.cache_data`) vivono in-process | Più istanze dietro un load balancer, stato/cache condivisi esternamente | 🔴 Oggi regge finché un'istanza basta per il traffico concorrente — invariato |
| **Database** | ✅ Risolto (2026-10-04): pooling esplicito su Postgres (`pool_pre_ping`, `pool_size=5`, `max_overflow=10`) e migrazioni versionate con Alembic (`migrations/`, migrazione iniziale verificata su SQLite e in CI) | Postgres gestito con pooling dimensionato, migrazioni versionate, read replica se serve | 🟡 Pooling e migrazioni ci sono; dimensionamento e read replica restano da validare sotto carico reale |
| **Audit/compliance** | ✅ Risolto in parte (2026-10-04): tabella `audit_log` + `log_audit()`, loggati salvataggio portafoglio e analisi eseguita; consultabile nella vista Admin | Audit trail completo (inclusi login, letture) per accessi e modifiche | 🟡 Copre le scritture principali, non ogni azione |
| **RBAC** | ✅ Risolto in parte (2026-10-04): ruolo `admin` via allowlist (`is_admin`, secrets `admin_emails`), vista Admin dedicata con statistiche cross-tenant e audit log | Ruoli differenziati (advisor, admin, sola lettura), gestiti non solo da una allowlist statica | 🟡 Un ruolo oltre "advisor"; manca sola-lettura e gestione self-service |
| **Rate limit su dati esterni** | Solo retry/backoff lato provider (`portfolio_intelligence/data/providers.py`); nessun throttling per-tenant: tanti advisor concorrenti possono competere sullo stesso budget di chiamate a EODHD/Yahoo | Quote per tenant, cache condivisa per non rifare le stesse chiamate | 🟡 Funziona a basso volume, non testato ad alto volume — invariato |
| **SLA/monitoring/backup** | Nessun monitoring applicativo, nessuna strategia di backup/DR documentata | SLA dichiarato, alerting, backup periodici testati | 🔴 Assente — invariato |

**Chi possiamo servire oggi**: un numero ridotto di consulenti/advisor
indipendenti o piccoli studi — self-hosted (Docker) o su Streamlit Community
Cloud con Postgres — con OIDC configurato esplicitamente e traffico
concorrente basso. Decine di utenti, non centinaia; isolamento e audit ora
verificabili (vista Admin), ma nessun SLA o garanzia di scalabilità multi-istanza.

**Cosa resta prima di parlare con un cliente enterprise**: OIDC obbligatorio
by default (non solo opt-in via `REQUIRE_AUTH`), deployment multi-istanza con
stato condiviso esterno, monitoring/SLA/backup. Isolamento (parziale), RBAC,
audit trail e pooling/migrazioni DB sono stati chiusi il 2026-10-04 — restano
scalabilità orizzontale e osservabilità operativa.

---

## Principi non negoziabili

1. **Onestà dei numeri prima delle feature**: mai mostrare una stima senza dichiararne i limiti (già oggi: caption "non è una previsione", survivorship bias dichiarato, euristiche documentate nei tooltip).
2. **Nessuna chiamata di rete nei test**: tutto mockato, CI deterministica (vale oggi, vale sempre).
3. **Ogni bug reale trovato diventa un test di regressione** (finora: dropna che cancellava lo storico, covarianza non allineata, pytest vs sys.path in CI).
4. **Non è consulenza finanziaria**: disclaimer ovunque l'output possa essere scambiato per un consiglio.
