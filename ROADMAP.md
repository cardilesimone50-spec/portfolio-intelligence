# ROADMAP — Portfolio Intelligence

> Obiettivo: diventare il miglior software open-source di Portfolio Intelligence.
> Documento di lavoro del CTO — aggiornato al 2026-07-11.

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

Stato: ✅ LICENSE MIT · ✅ conversione EUR con rischio cambio (toggle, default ON)
· ✅ rendimento annualizzato composto · ✅ risk-free configurabile per
Sharpe/Sortino — restano: parser broker su file reali (P1-8), deploy pubblico.

---

## Stato attuale

- ~3.600 righe Python; engine a package (`data / portfolio / analytics / fundamentals / visualization`), dashboard Streamlit (`app.py`, 857 righe), 84 test unitari verdi, CI GitHub Actions.
- Dati: Yahoo Finance (yfinance), storico Nasdaq-100 in SQLite (~122k righe) con aggiornamento incrementale.
- Funzionalità: metriche di rischio (Sharpe, Sortino, VaR, drawdown, beta/alpha), correlazioni, Markowitz + frontiera, backtest, check-up con score, report PDF, import CSV/Excel, portafogli salvati.

---

## 1. Problemi (in ordine di priorità)

### P0 — Bloccanti per l'obiettivo open-source

| # | Problema | Dettaglio |
|---|----------|-----------|
| 1 | **Nessuna LICENSE** | Senza licenza il codice non è open source: nessuno può legalmente usarlo o contribuire. Scegliere MIT (adozione massima) o AGPL (protegge da SaaS chiusi). |
| 2 | **Rischio cambio ignorato** | Gli importi sono in EUR ma i prezzi in USD. Rendimenti e VaR "in euro" ignorano l'EUR/USD: per un investitore europeo su titoli USA il cambio può dominare il risultato. Serve la serie EURUSD=X e la conversione delle equity curve. |
| 3 | **Annualizzazione aritmetica** | "Guadagno atteso = media giornaliera × 252" sovrastima sistematicamente rispetto al rendimento composto (CAGR), proprio il numero mostrato più in grande a un utente retail. Passare al geometrico o etichettare onestamente. |
| 4 | **Fonte dati unica e fragile** | yfinance usa API non ufficiali Yahoo: rate-limit, cambi di schema improvvisi, nessuna garanzia. Serve un layer provider astratto + almeno un fallback (es. Stooq per i prezzi) e retry/backoff. |

### P1 — Correttezza e affidabilità

| # | Problema | Dettaglio |
|---|----------|-----------|
| 5 | **Risk-free = 0** | Sharpe/Sortino calcolati con tasso zero in un mondo a tassi positivi: sovrastimati. Prendere il T-bill 3M (^IRX) come default. |
| 6 | **Survivorship bias nel backtest** | L'universo usa i componenti *attuali* del Nasdaq-100: le strategie (soprattutto momentum) risultano gonfiate. Serve lo storico dei constituent (dataset pubblici o snapshot periodici nel DB). |
| 7 | **Backtest senza costi** | Nessun costo di transazione/slippage: il momentum trimestrale su 10 titoli ruota molto e in realtà renderebbe meno. Aggiungere bps configurabili per ribilanciamento. |
| 8 | **Import Fineco/ISIN irrisolto** | L'importer generico gestisce sinonimi e preamboli ma senza file reali dei broker non è garantito. Manca la risoluzione ISIN→ticker (OpenFIGI API, gratuita) e il suffisso di mercato (.MI, .DE) per i titoli non-USA. |
| 9 | **`Ticker.info` sequenziale** | I fondamentali fanno 1 richiesta HTTP per ticker in loop: 10 titoli = ~10s. Parallelizzare (ThreadPool) e cachare su disco con TTL. |
| 10 | **Nessun logging** | Solo `print` negli script; in caso di errore dati non c'è traccia diagnostica. Introdurre `logging` strutturato. |

### P2 — Architettura e manutenzione

| # | Problema | Dettaglio |
|---|----------|-----------|
| 11 | **app.py monolite (857 righe)** | Tutte le 6 tab in un file: UI non testabile, merge conflict garantiti appena si è in due. Spacchettare in `src/ui/` (una view per tab) + testare con `streamlit.testing.AppTest`. |
| 12 | **Accoppiamento implicito tra tab** | Le tab condividono variabili globali di script (`amounts`, `computed`): l'ordine dei blocchi è vincolante e fragile. Servono uno stato applicativo esplicito (dataclass in `st.session_state`). |
| 13 | **Packaging non standard** | Import `from src.x import y`: non installabile via pip, il nome `src` è generico. Migrare a `pyproject.toml` con package `portfolio_intelligence`, entry point CLI. |
| 14 | **Costanti duplicate** | `TRADING_DAYS = 252` definito in 5 moduli; euristica `min_periods` copiata in più punti; soglie degli score sparse. Centralizzare in `config.py`. |
| 15 | **DB senza migrazioni né manutenzione** | Schema creato ad-hoc in `_connect`; `load_prices()` pivota tutto in memoria a ogni chiamata (nessuna query per range di date); tabella `analyses` a crescita illimitata. |
| 16 | **CI minima** | Solo pytest su un solo Python. Aggiungere ruff (lint+format), mypy, coverage con soglia, matrice 3.11/3.12/3.13. |

### P3 — Esperienza e portata

| # | Problema | Dettaglio |
|---|----------|-----------|
| 17 | **Solo italiano, stringhe hardcoded** | Per un progetto open-source internazionale serve i18n (EN default, IT) con catalogo messaggi. |
| 18 | **Universo solo Nasdaq-100** | S&P 500, STOXX 600, FTSE MIB, watchlist custom. |
| 19 | **PDF senza grafici** | Il report è solo testo/tabelle: aggiungere chart (matplotlib → immagine embedded). |
| 20 | **Nessuna storia di deploy** | Niente Dockerfile, niente guida Streamlit Cloud, secrets non gestiti. |

---

## 2. Debito tecnico (ripagabile in ~1 settimana di lavoro)

- [ ] `save_prices`: `PerformanceWarning` per DataFrame frammentato (copy prima del melt).
- [ ] `load_market_db()` non è cachato: ricarica e ripivota 122k righe a ogni interazione UI → `@st.cache_data` con invalidazione su mtime del DB.
- [ ] Session state del `data_editor` perso a ogni reload del codice: caricare all'avvio l'ultimo portafoglio salvato.
- [ ] `git config user.name/email` non configurati (warning a ogni commit).
- [ ] `fundamentals_report.py` e `analyze_nasdaq100.py` duplicano logica dell'app: ridurli a thin wrapper dell'engine.
- [ ] Indice temporale naive (no timezone): esplicitare UTC.
- [ ] Validazione input dal DB assente (una riga corrotta crasha il pivot).
- [ ] Cartella `data/` contiene ancora i CSV legacy accanto al DB: rimuovere il fallback CSV dopo un periodo di grazia.

---

## 3. Miglioramenti a funzionalità esistenti

1. **Backtest**: costi di transazione, ribilanciamento configurabile (mensile/trimestrale/annuale), metriche per strategia (Sharpe, max DD, turnover), walk-forward.
2. **Ottimizzazione**: vincoli utente (peso max per titolo/settore), shrinkage della covarianza (Ledoit-Wolf), Black-Litterman come opzione avanzata.
3. **VaR**: aggiungere CVaR (expected shortfall) e VaR parametrico accanto allo storico; orizzonti multipli.
4. **Score/DNA**: percentili rispetto all'universo invece di soglie assolute (più robusti tra settori); documentare la metodologia in `docs/METHODOLOGY.md`.
5. **Alert**: canale push reale — script `check_alerts.py` schedulabile via cron + notifica Telegram/email (richiede credenziali utente).
6. **Galaxy/Radar**: legenda interattiva, drill-down sul titolo cliccato.

---

## 4. Nuove funzionalità (ordinate per rapporto valore/sforzo)

| Priorità | Feature | Note |
|----------|---------|------|
| Alta | **Supporto multi-valuta** | Conversione EUR/USD/GBP con serie FX di Yahoo; risolve anche P0-2. |
| Alta | **Risoluzione ISIN → ticker** | OpenFIGI (gratuita, key opzionale): sblocca gli import broker reali. |
| Alta | **Deploy pubblico** | Dockerfile + guida Streamlit Cloud; a quel punto (e solo allora) autenticazione multi-utente. |
| Media | **Universi aggiuntivi** | S&P 500 (lista Wikipedia stabile), FTSE MIB, watchlist custom salvate nel DB. |
| Media | **Monte Carlo** | Simulazione di scenari sul portafoglio (bootstrap dei rendimenti storici), fan chart del valore a 1-5 anni. |
| Media | **Factor analysis reale** | Regressione dei rendimenti su fattori (mercato, size, value, momentum) — completa il modulo `analytics`. |
| Media | **Export Excel** | Il gemello del PDF per chi lavora in spreadsheet. |
| Bassa | **API REST (FastAPI)** | Separa engine e UI; abilita app mobile/terze parti. Solo dopo il packaging (P2-13). |
| Bassa | **PyPI** | Pubblicare l'engine come libreria `portfolio-intelligence`. |

---

## 5. Piano di rilascio proposto

### v0.2 — "Open Source Ready" (1-2 settimane)
LICENSE (MIT) · CONTRIBUTING.md · README inglese con screenshot · ruff+mypy+coverage in CI · pyproject.toml e rinomina package · spacchettamento app.py · logging.

### v0.3 — "Numeri onesti" (2-3 settimane)
Multi-valuta EUR/USD · rendimento geometrico · risk-free reale · costi nel backtest · CVaR · provider dati astratto con fallback e retry · fondamentali paralleli con cache.

### v0.4 — "Import per tutti" (2 settimane)
OpenFIGI ISIN→ticker · suffissi di mercato · parser dedicati per broker costruiti su file di esempio reali (raccolti dalla community con issue template dedicato) · universi S&P 500 e FTSE MIB.

### v1.0 — "Prodotto" (1-2 mesi)
Deploy pubblico con auth · alert Telegram/email schedulati · Monte Carlo · factor analysis · i18n EN/IT · storico constituent per backtest senza survivorship bias.

---

## Principi non negoziabili

1. **Onestà dei numeri prima delle feature**: mai mostrare una stima senza dichiararne i limiti (già oggi: caption "non è una previsione", survivorship bias dichiarato, euristiche documentate nei tooltip).
2. **Nessuna chiamata di rete nei test**: tutto mockato, CI deterministica (vale oggi, vale sempre).
3. **Ogni bug reale trovato diventa un test di regressione** (finora: dropna che cancellava lo storico, covarianza non allineata, pytest vs sys.path in CI).
4. **Non è consulenza finanziaria**: disclaimer ovunque l'output possa essere scambiato per un consiglio.
