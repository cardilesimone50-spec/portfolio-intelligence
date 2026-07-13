# Portfolio Intelligence — dossier enterprise

> Risposte oneste alle domande che una banca farebbe. Aggiornato al 2026-07-13.
> Stato: MVP dimostrabile, non ancora un prodotto bancario. Questo documento
> distingue esplicitamente ciò che c'è da ciò che manca.

## 1. Integrazione dati (API, import automatico)

**Oggi**: inserimento manuale, import CSV/Excel della posizione titoli,
portafogli salvati in SQLite, aggiornamento prezzi incrementale. I prezzi
passano da una **catena di provider astratta** (`src/data/providers.py`):
EODHD (licenza commerciale, si attiva con `EODHD_API_KEY`) → Yahoo → Stooq.
Sostituire la sorgente con il feed licenziato della banca è cambiare un
provider nella catena, non riscrivere l'app.
**Per una banca**: serve un'API `POST /portfolios/{client_id}` alimentata dai
sistemi della banca. L'engine è già separato dalla UI (package `src/`), quindi
esporlo via FastAPI è un lavoro di settimane, non mesi. Il collo di bottiglia
non è tecnico: è l'accordo con la banca su tracciato dati e autenticazione.

## 2. Compliance (MiFID II)

- **Informazione, non consulenza**: il sistema descrive caratteristiche
  misurabili del portafoglio ("concentrazione del 40% su un titolo") e non
  emette raccomandazioni personalizzate di investimento ("vendi X, compra Y").
  Le "simulazioni" mostrano l'effetto aritmetico di una modifica, dichiarandolo.
  Ogni output porta il disclaimer "non è una previsione né consulenza".
  **Nota**: il confine informazione/consulenza in ottica MiFID II va validato
  da un legale prima di qualunque uso commerciale — non è opzionale.
- **Niente conflitti di interesse**: il sistema non vende prodotti, non riceve
  retrocessioni, non ha inventario. Segnala rischi, non strumenti da comprare.
- **Algoritmi documentati**: ogni punteggio è una formula dichiarata nel codice
  e nella UI (tooltip). Nessun modello generativo nel percorso di analisi: il
  testo "da analista" è composto da regole deterministiche testate
  (`src/analytics/insights.py`, riproducibilità coperta da test).

## 3. Sicurezza

**Oggi (MVP)**: esecuzione locale o Streamlit Cloud; dati in SQLite sul
filesystem; nessuna autenticazione; nessuna crittografia at-rest; log assenti.
**Adeguamento enterprise (da fare, stimabile in 4-8 settimane)**: deploy su
cloud UE (es. AWS eu-south-1 / OVH), Postgres con cifratura at-rest, TLS,
SSO/OIDC della banca, audit log, backup, pen test di terza parte. Nessuna di
queste voci è un'incognita tecnica: sono lavoro noto.

## 4. Dashboard consulente

**Implementata (vista "Clienti")**: ogni portafoglio salvato è un cliente;
il consulente vede semaforo, valore, Health Score e il problema più urgente
di tutto il libro in una schermata. Con l'API del punto 1 diventa il vero
prodotto B2B: "chi dei miei 200 clienti devo chiamare oggi".

## 5. Report white-label

**Oggi**: PDF brandizzato Portfolio Intelligence con disclaimer.
**Da fare**: logo/colori/ragione sociale della banca parametrici, firma del
consulente, archivio report. Lavoro di giorni sul generatore esistente
(`src/visualization/pdf_report.py`).

## 6. Benchmark contro il profilo cliente

**Implementato**: profilo di rischio (prudente/moderato/aggressivo) con soglie
di volatilità dichiarate (10%/18%/30% annuo); il check-up segnala lo
sforamento in testa ai problemi ("oscilla il 13% in più della soglia del
profilo"). Confronto con "portafogli simili" richiede dati che oggi non
abbiamo: non lo simuliamo.

## 7. AI spiegabile

È il principio fondante del prodotto: nessuna black box. Ogni frase mostrata
deriva da una metrica calcolata, con soglie esplicite e fonte dati dichiarata
(Yahoo Finance oggi; per una banca, il suo data provider licenziato — vedi
ROADMAP, P0-4: i dati Yahoo non sono rivendibili commercialmente).

## 8. Storico e monitoraggio

**Implementato**: ogni analisi salvata registra data, valore, rendimento,
rischio e Health Score; il check-up mostra l'evoluzione dello score nel tempo.
**Da fare per una banca**: snapshot giornaliero automatico server-side (banale
una volta che esiste il deploy del punto 3).

## 9. White label completo

Dominio, tema e gestione utenti della banca: dipende dai punti 1 e 3.
Il tema è già centralizzato (CSS custom, un accent color): parametrizzarlo
è lavoro di giorni.

## 10. Business case (ordine di grandezza, ipotesi dichiarate)

Ipotesi: banca con 10.000 clienti affluent (AUM medio 100k€ → 1 mld€ AUM).
Se lo strumento contribuisce a trattenere anche solo lo 0,5% di AUM che
sarebbe migrato (5 mln€) con margine dell'1%, vale ~50k€/anno di margine
protetto — più il valore commerciale della vista consulente (prioritizzazione
delle chiamate) e del report brandizzato nei colloqui periodici MiFID.
Prezzo di riferimento di mercato per tool advisory white-label: 50-150k€/anno.
**Questi numeri sono ipotesi da validare con la banca, non previsioni.**

---

### In sintesi per il decisore

| Richiesta banca | Stato |
|---|---|
| Motore di analisi spiegabile e testato | Fatto (109 test) |
| Dashboard consulente multi-cliente | Fatto (MVP) |
| Profilo di rischio cliente | Fatto |
| Storico dello score | Fatto |
| Report PDF | Fatto (white-label parziale) |
| API di integrazione | Da fare (settimane, engine pronto) |
| Sicurezza enterprise + cloud UE | Da fare (4-8 settimane) |
| Provider dati astratto (EODHD/Yahoo/Stooq) | Fatto — serve solo la key EODHD |
| Moat legale (source-available, no rivendita SaaS) | Fatto — Elastic License 2.0 |
| Dati con licenza commerciale attivi in produzione | Da fare (chiave + contratto) |
| Parere legale MiFID II | Da fare (bloccante per produzione) |
