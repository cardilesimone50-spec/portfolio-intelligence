# Informativa sul trattamento dei dati personali

*Ai sensi degli artt. 13 e 14 del Regolamento (UE) 2016/679 ("GDPR") e del D.Lgs. 196/2003. Ultimo aggiornamento: {{updated}}.*

## 1. Titolare del trattamento

- **Titolare**: {{name}}
- **Indirizzo**: {{address}}
- **Partita IVA**: {{vat}}
- **Contatto per le richieste privacy**: {{email}}
- **PEC**: {{pec}}

## 2. Il servizio in breve

Smarteefinance è uno strumento informativo di analisi di portafogli azionari, in due modalità:

- **Investor**: uso libero, senza registrazione.
- **Advisor**: area riservata ai professionisti, con accesso tramite login (OpenID Connect).

## 3. Quali dati trattiamo, perché e su quale base giuridica

### 3.1 Modalità Investor (senza registrazione)

| Dati | Finalità | Base giuridica | Conservazione |
|---|---|---|---|
| Posizioni inserite (simboli dei titoli, quantità, date e prezzi di acquisto) e contenuto dei file importati | Calcolare l'analisi richiesta | Esecuzione del servizio richiesto (art. 6.1.b) | Solo per la durata della sessione del browser: **non vengono salvati** in alcun database |
| Dati tecnici di navigazione (indirizzo IP, data e ora, tipo di browser) registrati dal fornitore di hosting | Erogazione e sicurezza del sito | Legittimo interesse alla sicurezza (art. 6.1.f) | Secondo le politiche del fornitore di hosting (§5) |

Non chiediamo nome, email o altri dati identificativi. **Attenzione**: gli estratti esportati dal broker possono contenere il nome dell'intestatario o il numero di conto. Il file viene letto solo in memoria e non viene conservato, ma ti consigliamo di eliminare queste colonne prima del caricamento.

### 3.2 Modalità Advisor (area riservata)

| Dati | Finalità | Base giuridica | Conservazione |
|---|---|---|---|
| Dati dell'account ricevuti dal fornitore di identità (email, nome) | Autenticazione e separazione dei dati tra consulenti | Esecuzione del contratto (art. 6.1.b) | Fino alla cancellazione dell'account |
| Portafogli dei clienti salvati e storico delle analisi | Erogazione del servizio al consulente | Esecuzione del contratto (art. 6.1.b) | Fino alla cancellazione da parte del consulente |
| Registro di sicurezza (chi ha fatto cosa e quando) | Sicurezza e accertamento di abusi | Legittimo interesse (art. 6.1.f) | {{audit_retention}}; alla cancellazione dell'account l'email è sostituita da un codice casuale non derivato da essa e i dettagli sono rimossi |

**Dati dei clienti del consulente.** Per i dati dei propri clienti il consulente agisce come **titolare** del trattamento, mentre {{name}} agisce come **responsabile** ai sensi dell'art. 28 GDPR, sulla base di un accordo sul trattamento dei dati da sottoscrivere prima dell'uso professionale. Raccomandiamo di identificare i portafogli con codici interni e non con nomi e cognomi.

## 4. Natura del conferimento

Il conferimento dei dati è facoltativo, ma senza le posizioni non è possibile calcolare l'analisi. Per l'area Advisor l'accesso è necessario.

## 5. Destinatari e trasferimenti fuori dall'UE

I dati possono essere trattati da fornitori che agiscono come responsabili del trattamento:

- **Hosting dell'applicazione**: {{hosting}}. Se il fornitore ha sede negli Stati Uniti, il trasferimento avviene sulla base dell'EU-U.S. Data Privacy Framework o delle Clausole Contrattuali Standard della Commissione europea.
- **Login (solo Advisor)**: il fornitore di identità scelto per l'accesso (ad esempio Google LLC), che riceve i dati necessari all'autenticazione secondo la propria informativa.
- **Fornitori di dati di mercato** (Yahoo Finance, SEC EDGAR, Banca Centrale Europea, Tesoro degli Stati Uniti e, se attivati, Stooq ed EODHD): ricevono dal nostro server **solo le richieste di dati di mercato** (per esempio i simboli dei titoli), mai dati che ti identificano.

I dati non vengono venduti né usati per pubblicità o profilazione.

## 6. Decisioni automatizzate

L'Health Score e gli altri indicatori sono calcoli descrittivi sul portafoglio. Non producono decisioni con effetti giuridici o significativi sulla persona ai sensi dell'art. 22 GDPR.

## 7. Minori

Il servizio è rivolto a persone maggiorenni e non è destinato ai minori di 18 anni.

## 8. I tuoi diritti

Puoi chiedere in qualsiasi momento l'accesso ai tuoi dati, la rettifica, la cancellazione, la limitazione del trattamento e la portabilità, e puoi opporti al trattamento basato sul legittimo interesse (artt. 15-22 GDPR), scrivendo a {{email}}. Risponderemo entro un mese.

Nell'area Advisor puoi cancellare in autonomia un singolo portafoglio cliente, oppure tutti i tuoi dati, dalla sezione **Privacy e dati** della barra laterale.

Hai inoltre il diritto di proporre reclamo al Garante per la protezione dei dati personali (www.garanteprivacy.it).

## 9. Modifiche

Eventuali modifiche a questa informativa saranno pubblicate su questa pagina con la nuova data di aggiornamento.
