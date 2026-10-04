# Audit di compliance, pratiche commerciali e accessibilità

> Data: 2026-10-04. Perimetro: codice del repository (Investor, Advisor, profilo di
> scelta), comportamento verificato nel browser e dipendenze.
> **Non è un parere legale.** I testi in `docs/legal/` sono bozze tecniche
> accurate rispetto al codice, ma vanno validati da un avvocato prima della
> pubblicazione, insieme al parere MiFID già indicato come bloccante in
> `docs/ENTERPRISE.md`.

Legenda: ✅ conforme · 🔧 corretto in questo intervento · ⚠️ serve una tua azione · ➖ non applicabile oggi.

## Priorità per te (in ordine)

1. ⚠️ **Nome e contatto del titolare**: anche senza società né attività commerciale, l'informativa privacy deve indicare chi è il titolare e come contattarlo (art. 13 GDPR). Bastano nome e un'email, nella sezione `[legal]` dei secrets di Streamlit Cloud: così non finiscono nel repository. Partita IVA, REA e PEC non servono finché non c'è un'attività economica: quelle righe non compaiono.
2. ⚠️ **Dati Yahoo nel repository pubblico**: `data/nasdaq100_prices.csv` e `data/nasdaq100_fundamentals.csv` ridistribuiscono a chiunque dati Yahoo Finance. Le condizioni di Yahoo ne limitano l'uso a fini personali. Il repository è pubblico su GitHub. Vedi §19.
3. ⚠️ **Parere legale MiFID/TUF** prima di qualunque uso commerciale, in particolare per l'ottimizzazione media-varianza dell'area Advisor, che propone pesi di portafoglio.
4. ⚠️ **Accordo sul trattamento dei dati (DPA, art. 28 GDPR)** da far firmare ai consulenti prima dell'uso professionale: per i dati dei loro clienti tu sei responsabile del trattamento.
5. ⚠️ **Durata di conservazione del registro di sicurezza** (audit log): va decisa e poi applicata con una cancellazione periodica, che oggi non esiste.

---

## A. Documentazione legale e consensi

### 1. Privacy policy — 🔧 creata
Prima non esisteva. Nuovo file `docs/legal/privacy.md`, raggiungibile da `?legal=privacy`. Copre le due modalità:
- **Investor**: niente account, posizioni solo nella sessione del browser.
- **Advisor**: account via login, portafogli dei clienti con ruolo di responsabile ex art. 28.

Documenta anche fornitori, trasferimenti extra-UE, conservazione, diritti e reclamo al Garante. È scritta su ciò che il codice fa davvero: per esempio i fornitori di dati di mercato ricevono solo i simboli dei titoli.

### 2. Termini di servizio — 🔧 creati
`docs/legal/termini.md`. Contengono la natura informativa (non consulenza ai sensi di TUF e MiFID II), il limite di 18 anni, l'assenza di garanzia sui dati di terzi, gli usi vietati e i limiti di responsabilità entro l'art. 1229 c.c. e il Codice del Consumo. Il foro è quello del consumatore (art. 66-bis).

Non c'è il link alla piattaforma europea ODR, che è stata dismessa nel luglio 2025.

### 3. Refund policy — ➖ non applicabile oggi
Il servizio è gratuito e non ci sono pagamenti. Ho preparato `docs/legal/rimborsi-bozza.md`, **non pubblicata**, con recesso di 14 giorni, contenuto digitale (art. 59 lett. o), disdetta online facile quanto la sottoscrizione e clienti B2B. Va pubblicata solo quando esisterà un piano a pagamento.

### 4. Cookie policy — 🔧 creata
`docs/legal/cookie.md`, con l'elenco **verificato nel browser e nel codice di Streamlit 1.59**:

| Nome | Tipo | Durata |
|---|---|---|
| `_streamlit_xsrf` | Cookie tecnico anti-CSRF | Sessione |
| `_streamlit_user`, `_streamlit_user_tokens` | Login Advisor | Massimo 30 giorni |
| `stSidebarCollapsed-*`, `stActiveTheme-*` | Preferenze dell'interfaccia (localStorage) | Fino alla cancellazione dei dati del sito |

### 5. Cookie banner — ✅ non necessario
Ci sono solo strumenti tecnici: niente analytics, pubblicità o profilazione. Le statistiche d'uso di Streamlit sono già disattivate (`gatherUsageStats = false`). Per l'art. 122 del Codice privacy e le Linee guida del Garante del 10/06/2021 non serve il consenso, e un banner che lo chiede sarebbe fuorviante.

**Attenzione**: se in futuro aggiungi analytics o pixel, servirà un banner con blocco preventivo, rifiuto facile quanto l'accettazione e nessuna casella pre-selezionata.

### 6. Checkbox di consenso nei moduli — ✅ nessuna dovuta
Nessun trattamento si basa sul consenso: le basi sono contratto e legittimo interesse. Aggiungere una casella "acconsento al trattamento" sarebbe scorretto, perché il consenso non può essere condizione per usare il servizio.

Le uniche caselle presenti sono le **conferme** delle cancellazioni irreversibili (§20), non pre-selezionate.

## B. Gestione dei dati

### 7. Nessun dato superfluo — ✅
I moduli chiedono solo titolo, quantità, data e prezzo, più il nome del portafoglio in Advisor. Niente nome, email o telefono. L'import del broker estrae solo le colonne di titolo, quantità, prezzo e importo, e scarta le altre.

La privacy avvisa che gli estratti del broker possono contenere il nome dell'intestatario. **Consiglio per Advisor**: identifica i portafogli con codici interni e non con nomi e cognomi dei clienti; è scritto anche nell'informativa.

### 8. Audit di SDK e servizi terzi — 🔧 un trasferimento rimosso

| Componente | Dove gira | Dati verso terzi | Esito |
|---|---|---|---|
| **Google Fonts** (Inter, Space Grotesk) | Browser dell'utente | IP dell'utente verso Google a ogni visita | 🔧 **Rimosso.** Una sentenza del Tribunale di Monaco (LG München I, 3 O 17493/20) l'ha giudicato illecito senza consenso. Ora si usa Source Sans, servito da Streamlit stesso. Verificato: zero richieste esterne dal browser. |
| Streamlit 1.59 | Server e browser | Nessuna (statistiche disattivate) | ✅ |
| Yahoo Finance / Stooq / EODHD | Server | Solo simboli dei titoli | ✅ privacy; ⚠️ licenza, vedi §19 |
| Provider di login OIDC (Google) | Advisor | Dati di autenticazione | ✅ dichiarato nella privacy |
| Hosting (Streamlit Community Cloud / Snowflake, USA) | Server | IP e log tecnici | ⚠️ inserisci il fornitore in `hosting` e verifica che le sue condizioni consentano l'uso previsto |
| Postgres (se `DATABASE_URL`) | Server | Portafogli Advisor | ⚠️ scegli un fornitore UE e firma il suo DPA |
| pandas, numpy, scipy, altair, reportlab, openpyxl, pdfplumber, SQLAlchemy, alembic, requests, lxml | Server | Nessuna | ✅ licenze permissive (BSD/MIT/Apache) |
| psycopg | Server | Nessuna | ✅ LGPL, usato come libreria non modificata |

### 17. Consenso dei genitori per i minori — ✅ flusso non necessario
L'area Investor non ha account e non conserva dati. L'area Advisor è per professionisti. Termini e privacy dichiarano che il servizio è per maggiorenni, coerente con un prodotto finanziario.

Un flusso di consenso genitoriale servirebbe solo se si raccogliessero dati di minori (in Italia sotto i 14 anni, art. 2-quinquies del Codice privacy), cosa che non avviene.

### 20. Cancellazione dei dati — 🔧 implementata
Prima esisteva solo una funzione interna `delete_portfolio`, senza interfaccia, che lasciava storico delle analisi e nome del cliente nell'audit log.

Ora, nella barra laterale Advisor:
- **Elimina portafoglio cliente**: cancella composizione e storico analisi, e oscura il nome del cliente nel registro di sicurezza.
- **Privacy e dati → Elimina tutti i miei dati**: cancella tutti i portafogli e le analisi del consulente. Le voci di registro restano ma vengono pseudonimizzate (hash non reversibile).

Entrambe le azioni richiedono una casella di conferma. Sono coperte da test, sia sulla base dati sia sull'interfaccia, e non toccano i dati degli altri consulenti. In Investor non c'è nulla da cancellare.

Restano manuali, via email come indicato nella privacy: le richieste di chi non ha accesso all'app e i log dell'hosting.

## C. Trasparenza e pratiche commerciali

### 9. Dark pattern — ✅
Non ci sono flussi di acquisto o disdetta. Ho verificato: nessuna casella pre-selezionata, nessun conto alla rovescia o finta scarsità, nessun "conferma per vergogna". Le cancellazioni sono esplicite e richiedono conferma.

### 10. Costi nascosti — ➖
Non ci sono pagamenti. "Investor non costa nulla da provare" è vero.

### 11. Recensioni false — ✅
Nessuna recensione, testimonianza, valutazione a stelle o "usato da" nel codice.

### 12. Affermazioni non supportate — 🔧 corrette

| Testo precedente | Problema | Ora |
|---|---|---|
| "Strumento… **indipendente**" e "Analisi **indipendente**" | In finanza "indipendente" richiama la consulenza indipendente regolata (TUF art. 24-bis) | "Strumento informativo di analisi del portafoglio" e "Il tuo portafoglio azionario, misurato sui tuoi dati" |
| "Immediato e **anonimo**" | L'hosting registra l'IP: anonimo non è dimostrabile | "Senza registrazione… le posizioni restano nella sessione e non vengono salvate" |
| Advisor: "**versione storica** e confronto scenari" | Non esiste versionamento: il salvataggio sovrascrive | "Salvataggio dei portafogli e storico delle loro analisi" |
| Advisor: "PDF brandizzati… con **disclaimer personalizzati**" | I disclaimer sono fissi; il white-label è ancora da fare (ENTERPRISE §5) | "Report PDF per il cliente finale, con metodologia e avvertenze" |
| Advisor: "reportistica **istituzionale**", "Reportistica **custom**" | Enfasi non supportata | "reportistica per il cliente" |
| Opportunità: "includerli **ridurrebbe** la dipendenza dal ciclo tech" | Promessa di effetto, tono prescrittivo | Descrizione del fatto: "nessuna esposizione ai settori difensivi…" |

Verificate e mantenute: "103 titoli con storico e bilanci" (vero dopo lo snapshot), "6 componenti", "circa un minuto", "report di tre pagine", "scenari di shock" (`simulate_shock` esiste), "isolamento multi-tenant" (testato, con avviso se l'autenticazione è disattivata).

### 16. Dettagli legali — 🔧 adattati a un progetto privato, ⚠️ nome ed email da inserire
Il servizio è gratuito e non c'è attività commerciale. Per questo gli obblighi d'impresa (P.IVA sul sito, art. 35 D.P.R. 633/1972; informazioni dell'art. 7 D.Lgs. 70/2003) oggi non si applicano.

I documenti mostrano P.IVA, REA, PEC, indirizzo e foro **solo se configurati**: in caso contrario la riga sparisce. Hosting e data di aggiornamento hanno valori predefiniti.

Restano **obbligatori nome e contatto del titolare** per la privacy. Vanno inseriti nei secrets di Streamlit Cloud (Settings → Secrets), non nel repository:

```toml
[legal]
name = "Nome Cognome"
email = "indirizzo dedicato alle richieste privacy"
# solo se un giorno aprirai un'attività:
# address = "…"  vat = "…"  rea = "…"  pec = "…"  court = "…"
```

Il footer con i link legali è presente su tutte le schermate e i link si aprono in una nuova scheda, così la sessione non si perde.

### 18. Link di disiscrizione nelle email — ➖
L'app non invia email: non c'è SMTP, newsletter o email transazionali. Se in futuro arriveranno, servono un link di disiscrizione funzionante e il consenso per il marketing (art. 130 Codice privacy).

### 19. Licenze di font, immagini e dati — ⚠️ promemoria
- **Font**: Source Sans e Source Code (OFL 1.1) serviti da Streamlit ✅. Helvetica nel PDF è un font standard non incorporato ✅. Inter e Space Grotesk non sono più usati.
- **Icone**: Material Symbols (Apache 2.0) ✅. Gli emoji nell'interfaccia sono resi dai font del sistema operativo ✅.
- **Immagini**: nessuna immagine nel progetto ✅.
- **Dati di mercato** ⚠️: Yahoo Finance non concede licenza per uso commerciale né per ridistribuzione. Con il repository pubblico, i due CSV in `data/` sono di fatto ridistribuiti. Opzioni:
  - **(a)** rendere privato il repository (Streamlit Cloud supporta i repo privati);
  - **(b)** passare a EODHD, già supportato con `EODHD_API_KEY`, prima del lancio commerciale.
  
  Consiglio entrambe.
- **Marchio** ⚠️: verifica su EUIPO/UIBM che "Smarteefinance" non confligga con marchi registrati nel settore finanziario.
- **Codice**: Elastic License 2.0 ✅. Le dipendenze hanno licenze permissive (§8).

## D. Accessibilità (WCAG 2.1 AA)

### 13. Testi alternativi — ✅ / 🔧
Non ci sono tag `<img>`. Le icone SVG decorative ora hanno `aria-hidden="true"` 🔧, e così le sigle colorate dei titoli, che ripetono un testo già visibile accanto 🔧.

**Resta da fare**: i grafici Altair non hanno un'alternativa testuale. Andrebbe aggiunta una didascalia riassuntiva o una tabella dei dati sotto ciascun grafico (criterio 1.1.1).

### 14. Contrasto colori — 🔧 corretto
Rapporti calcolati con la formula WCAG:

| Elemento | Prima | Ora |
|---|---|---|
| Testo "guadagno" verde `#0ea371` | 3,23:1 ❌ | `#047857` → 5,48:1 |
| Valori ambra nell'Health Score `#d97706` | 3,19:1 ❌ | `#b45309` → 5,02:1 |
| Grigio `#94a3b8` (scelta profilo) | 2,56:1 ❌ | `#64748b` → 4,76:1 |
| Sigle bianche sui colori della palette | fino a 2,17:1 ❌ | colore del testo scelto per contrasto → minimo 4,52:1, verificato da test |

I colori originali restano nei grafici, dove la soglia per elementi non testuali è 3:1.

### 15. Navigazione da tastiera — ✅ / 🔧
- Tutti i controlli sono widget nativi di Streamlit, raggiungibili con Tab; nessuna regola CSS rimuove il focus ✅.
- Gli elementi HTML personalizzati non sono interattivi ✅.
- 🔧 I pulsanti "✕" e "···" avevano come nome per i lettori di schermo il simbolo; ora si chiamano "Rimuovi" e "Modifica".
- 🔧 La pagina dichiarava sempre `lang="en"`, anche in italiano (criterio 3.1.1); ora segue la lingua scelta (verificato nel browser).

**Non verificato**: un percorso completo da sola tastiera con un lettore di schermo reale (VoiceOver/NVDA). Te lo consiglio prima del lancio. Due limiti noti di Streamlit: manca un link "salta al contenuto" e i grafici non sono esplorabili da tastiera.

---

## File toccati da questo intervento

- **Nuovi**:
  - `portfolio_intelligence/ui/legal.py`
  - `docs/legal/{privacy,termini,cookie,note-legali,rimborsi-bozza}.md`
  - `tests/test_legal.py`
- **Modificati**:
  - tema e componenti (font, contrasto, footer, aria)
  - `data/store.py` (cancellazione)
  - `views/sidebar.py` (interfaccia di cancellazione)
  - `i18n.py` (affermazioni)
  - `router.py` e `app.py` (pagine legali prima del login, lingua del documento)
  - test di store e sidebar
