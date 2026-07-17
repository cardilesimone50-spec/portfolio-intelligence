"""Catalogo bilingue EN/IT e stato lingua dell'app.

Uso: `t(key, **kwargs)` traduce nella lingua corrente (default inglese, così
i test restano stabili); `t_in(lang, key, **kwargs)` traduce in una lingua
esplicita (usato dal PDF, che riceve `lang` come parametro).
Ogni voce del catalogo è (inglese, italiano); chiave mancante → torna la chiave.
"""

_EN, _IT = 0, 1
_LANG = "en"
LANGUAGES = {"en": "English", "it": "Italiano"}


def set_language(lang: str) -> None:
    global _LANG
    _LANG = lang if lang in LANGUAGES else "en"


def get_language() -> str:
    return _LANG


def t(key: str, **kwargs) -> str:
    return t_in(_LANG, key, **kwargs)


def t_in(lang: str, key: str, **kwargs) -> str:
    entry = _CATALOG.get(key)
    if entry is None:
        return key
    text = entry[_IT] if lang == "it" else entry[_EN]
    return text.format(**kwargs) if kwargs else text


_CATALOG: dict[str, tuple[str, str]] = {
    # ---------------------------------------------------------------- interpret
    "vol.low": (
        "Swings typical of a conservative portfolio.",
        "Oscillazioni tipiche di un portafoglio prudente.",
    ),
    "vol.mid": (
        "Swings typical of a diversified equity portfolio.",
        "Oscillazioni tipiche di un portafoglio azionario diversificato.",
    ),
    "vol.high": (
        "Elevated swings: expect wide moves.",
        "Oscillazioni elevate: attese escursioni ampie.",
    ),
    "vol.extreme": (
        "Swings of an aggressive single stock, not a portfolio.",
        "Oscillazioni da singolo titolo aggressivo, non da portafoglio.",
    ),
    "vol.percentile": (
        " Less volatile than {pct} of Nasdaq-100 single stocks.",
        " Meno volatile del {pct} dei singoli titoli del Nasdaq-100.",
    ),
    "sharpe.negative": (
        "Over the period the risk taken was not rewarded: "
        "you returned less than the risk-free rate.",
        "Nel periodo il rischio assunto non è stato ripagato: "
        "il rendimento è stato inferiore al tasso privo di rischio.",
    ),
    "sharpe.modest": (
        "Modest risk-adjusted return: below the 0.5-1 band typical of a "
        "diversified long-term equity portfolio.",
        "Rendimento corretto per il rischio modesto: sotto la banda 0,5-1 "
        "tipica di un azionario diversificato di lungo periodo.",
    ),
    "sharpe.inline": (
        "In line with what diversified equity has historically paid per unit of risk (0.5-1).",
        "In linea con quanto l'azionario diversificato ha storicamente pagato "
        "per unità di rischio (0,5-1).",
    ),
    "sharpe.good": (
        "Above the historical norm: each unit of risk was well paid.",
        "Sopra la norma storica: ogni unità di rischio è stata ben ripagata.",
    ),
    "sharpe.exceptional": (
        "Exceptional over the observed period: such values rarely persist.",
        "Eccezionale nel periodo osservato: valori simili raramente persistono.",
    ),
    "sortino.upside": (
        "Volatility skews to the upside: drops weigh less than gains (a good sign).",
        "La volatilità pende verso l'alto: i ribassi pesano meno dei rialzi (buon segno).",
    ),
    "sortino.downside": (
        "Volatility is concentrated in the downside: the drops hurt more.",
        "La volatilità è concentrata al ribasso: le discese fanno più male.",
    ),
    "sortino.symmetric": (
        "Drops and gains contributed symmetrically to volatility.",
        "Ribassi e rialzi hanno contribuito in modo simmetrico alla volatilità.",
    ),
    "dd.normal": (
        "Within a normal market correction (down to -10%).",
        "Entro una normale correzione di mercato (fino a -10%).",
    ),
    "dd.correction": (
        "Between a correction (-10%) and a bear market (-20%).",
        "Tra una correzione (-10%) e un mercato ribassista (-20%).",
    ),
    "dd.bear": (
        "Bear-market territory: drops like this test your discipline.",
        "Territorio da bear market: cali così mettono alla prova la disciplina.",
    ),
    "dd.severe": (
        "Severe drawdown: few investors hold through drops this deep without selling.",
        "Drawdown severo: pochi investitori reggono cali così profondi senza vendere.",
    ),
    "beta.defensive": (
        "More defensive than {benchmark}: you dampen market moves.",
        "Più difensivo del {benchmark}: i movimenti di mercato vengono attutiti.",
    ),
    "beta.inline": (
        "You move broadly in line with {benchmark}.",
        "Il portafoglio si muove sostanzialmente in linea col {benchmark}.",
    ),
    "beta.amplify": (
        "You amplify {benchmark} moves: steeper rises and falls.",
        "I movimenti del {benchmark} vengono amplificati: salite e discese più ripide.",
    ),
    "corr.identical": (
        "The holdings move almost identically: diversification is only apparent.",
        "I titoli si muovono quasi identici: la diversificazione è solo apparente.",
    ),
    "corr.close": (
        "The holdings move closely together: the diversification benefit is reduced.",
        "I titoli si muovono molto assieme: il beneficio di diversificazione è ridotto.",
    ),
    "corr.average": (
        "Average diversification for a portfolio within the same market.",
        "Diversificazione nella media per un portafoglio dentro lo stesso mercato.",
    ),
    "corr.independent": (
        "The holdings move independently: real, effective diversification.",
        "I titoli si muovono in modo indipendente: diversificazione reale ed efficace.",
    ),
    # ---------------------------------------------------------------- dna label
    "dna.aggressive_growth": ("Aggressive growth profile", "Profilo growth aggressivo"),
    "dna.growth": ("Growth profile", "Profilo growth"),
    "dna.value": ("Value profile", "Profilo value"),
    "dna.defensive": ("Defensive profile", "Profilo difensivo"),
    "dna.balanced": ("Balanced profile", "Profilo bilanciato"),
    # ---------------------------------------------------------------- executive summary
    "exec.ret": (
        "Over the period ({period}) the portfolio returned {ret}.",
        "Nel periodo ({period}) il portafoglio ha reso {ret}.",
    ),
    "exec.corr_weak": (
        "Diversification is weak: the holdings move very similarly "
        "(average correlation {corr}).",
        "La diversificazione è debole: i titoli si muovono in modo molto "
        "simile (correlazione media {corr}).",
    ),
    "exec.corr_good": (
        "The portfolio is well diversified (average correlation {corr}).",
        "Il portafoglio è ben diversificato (correlazione media {corr}).",
    ),
    "exec.corr_avg": (
        "Diversification is average (correlation {corr}).",
        "Diversificazione nella media (correlazione {corr}).",
    ),
    "exec.risk_conc": (
        "Risk is concentrated: {ticker} alone drives {share} of total variability.",
        "Il rischio è concentrato: {ticker} da solo guida il {share} della variabilità totale.",
    ),
    "exec.usd": (
        "US-dollar exposure is high ({share} of capital): "
        "the euro result also depends on the EUR/USD rate.",
        "L'esposizione al dollaro è alta ({share} del capitale): "
        "il risultato in euro dipende anche dal cambio EUR/USD.",
    ),
    "exec.dd_high": (
        "Historical downside risk is above average: over the period the "
        "portfolio fell as much as {dd} from its peak.",
        "Il rischio storico al ribasso è sopra la media: nel periodo il "
        "portafoglio è arrivato a perdere il {dd} dal massimo.",
    ),
    "exec.dd_low": (
        "Drops from the peak stayed contained (max {dd}).",
        "I cali dal massimo sono rimasti contenuti (max {dd}).",
    ),
    "exec.beta_high": (
        "With a beta of {beta} versus {benchmark}, the portfolio amplifies market moves.",
        "Con un beta di {beta} verso {benchmark}, il portafoglio amplifica "
        "i movimenti di mercato.",
    ),
    "exec.beta_low": (
        "With a beta of {beta} versus {benchmark}, the portfolio "
        "is more defensive than the market.",
        "Con un beta di {beta} verso {benchmark}, il portafoglio "
        "è più difensivo del mercato.",
    ),
    # ---------------------------------------------------------------- problems
    "prob.concentration": (
        "**{ticker}** is **{weight}** of the portfolio: high concentration risk.",
        "**{ticker}** è il **{weight}** del portafoglio: rischio di concentrazione alto.",
    ),
    "prob.risk_driver": (
        "**{ticker}** drives **{share} of total risk**.",
        "**{ticker}** guida il **{share} del rischio totale**.",
    ),
    "prob.correlation": (
        "Average correlation **{corr}**: the holdings move together, "
        "the portfolio rides a single engine.",
        "Correlazione media **{corr}**: i titoli si muovono assieme, "
        "il portafoglio viaggia su un motore solo.",
    ),
    "prob.dividend": (
        "Dividend yield **{dy}%**, below the market average: "
        "the portfolio generates little income.",
        "Dividend yield **{dy}%**, sotto la media di mercato: "
        "il portafoglio genera poco reddito.",
    ),
    "prob.volatility": (
        "Elevated volatility versus a balanced portfolio.",
        "Volatilità elevata rispetto a un portafoglio bilanciato.",
    ),
    # ---------------------------------------------------------------- opportunities
    "opp.defensive_sectors": (
        "Uncovered defensive sectors (**{sectors}**): "
        "adding them would reduce reliance on the tech cycle.",
        "Settori difensivi scoperti (**{sectors}**): includerli ridurrebbe "
        "la dipendenza dal ciclo tecnologico.",
    ),
    "opp.cheap": (
        "Among the holdings, **{ticker}** has the lowest multiples (P/E {pe}, P/S {ps}).",
        "Tra i titoli in portafoglio, **{ticker}** ha i multipli più bassi "
        "(P/E {pe}, P/S {ps}).",
    ),
    "opp.none": (
        "No obvious gaps against the monitored rules (defensive sectors, valuations).",
        "Nessuna lacuna evidente rispetto alle regole monitorate "
        "(settori difensivi, valutazioni).",
    ),
    # ---------------------------------------------------------------- suggestions
    "sugg.concentration": (
        "Concentration is high: **{ticker}** dominates risk. A common "
        "prudential guideline treats a single-stock weight above 25% as critical.",
        "La concentrazione è alta: **{ticker}** domina il rischio. Una prassi "
        "prudenziale diffusa considera critico un peso sopra il 25% su un singolo titolo.",
    ),
    "sugg.correlation": (
        "The holdings tend to move together: instruments from less-correlated "
        "sectors or regions generally reduce overall variability.",
        "I titoli tendono a muoversi assieme: strumenti di settori o aree "
        "meno correlati in genere riducono la variabilità complessiva.",
    ),
    "sugg.volatility": (
        "Volatility is high: in general, lower-beta components dampen the "
        "amplitude of a portfolio's swings.",
        "La volatilità è alta: in generale, componenti a beta più basso "
        "smorzano l'ampiezza delle oscillazioni di un portafoglio.",
    ),
    "sugg.multiples": (
        "The portfolio's average multiples are high (elevated P/E and P/S): "
        "the price embeds significant growth expectations.",
        "I multipli medi del portafoglio sono alti (P/E e P/S elevati): "
        "il prezzo incorpora attese di crescita significative.",
    ),
    "sugg.balanced": (
        "The portfolio looks balanced against the monitored rules: "
        "concentration, correlation, volatility and multiples.",
        "Il portafoglio appare bilanciato rispetto alle regole monitorate: "
        "concentrazione, correlazione, volatilità e multipli.",
    ),
    # ---------------------------------------------------------------- insights
    "ins.ret": (
        "The portfolio returned **{ret}** over the period ({period}).",
        "Il portafoglio ha reso **{ret}** nel periodo ({period}).",
    ),
    "ins.top2": (
        "**{t1}** and **{t2}** account for **{share} of the portfolio's total risk**.",
        "**{t1}** e **{t2}** valgono il **{share} del rischio totale del portafoglio**.",
    ),
    "ins.corr_high": (
        "Your holdings are tightly linked (average correlation **{corr}**): "
        "diversification is weak.",
        "I tuoi titoli sono strettamente legati (correlazione media **{corr}**): "
        "la diversificazione è debole.",
    ),
    "ins.corr_good": (
        "Good diversification: average correlation **{corr}**.",
        "Buona diversificazione: correlazione media **{corr}**.",
    ),
    "ins.drawdown": (
        "Over the period the portfolio suffered a maximum drop of **{dd}** from its peak.",
        "Nel periodo il portafoglio ha subito un calo massimo del **{dd}** dal picco.",
    ),
    "ins.beta_high": (
        "Beta **{beta}** vs {benchmark}: you amplify market moves.",
        "Beta **{beta}** vs {benchmark}: i movimenti di mercato vengono amplificati.",
    ),
    "ins.beta_low": (
        "Beta **{beta}** vs {benchmark}: you are more defensive than the market.",
        "Beta **{beta}** vs {benchmark}: sei più difensivo del mercato.",
    ),
    # ---------------------------------------------------------------- alerts
    "alert.risk_driver": (
        "**{ticker}** now drives **{share} of the portfolio's total risk**.",
        "**{ticker}** ora guida il **{share} del rischio totale del portafoglio**.",
    ),
    "alert.correlation": (
        "Average correlation rose to **{corr}**: the portfolio moves like a single stock.",
        "La correlazione media è salita a **{corr}**: il portafoglio si "
        "muove come un titolo solo.",
    ),
    "alert.drawdown": (
        "Deep drawdown: **{dd}** from the peak over the period.",
        "Drawdown profondo: **{dd}** dal massimo nel periodo.",
    ),
    "alert.session_marker": ("Last session", "Ultima seduta"),
    "alert.last_session": (
        "Last session: portfolio **{move}**. Main contributor: **{ticker}** "
        "({contrib} of the total).",
        "Ultima seduta: portafoglio **{move}**. Principale responsabile: "
        "**{ticker}** ({contrib} del totale).",
    ),
    # ---------------------------------------------------------------- component names
    "comp.Diversification": ("Diversification", "Diversificazione"),
    "comp.Concentration": ("Concentration", "Concentrazione"),
    "comp.Volatility": ("Volatility", "Volatilità"),
    "comp.Currency": ("Currency", "Valuta"),
    "comp.Drawdown": ("Drawdown", "Drawdown"),
    "comp.Quality": ("Quality", "Qualità"),
    "comp.Growth": ("Growth", "Crescita"),
    "comp.Value": ("Value", "Value"),
    "comp.Risk": ("Risk", "Rischio"),
    "comp.Correlation": ("Correlation", "Correlazione"),
    "comp.Valuation": ("Valuation", "Valutazione"),
    # ---------------------------------------------------------------- risk profiles
    "prof.Not set": ("Not set", "Non impostato"),
    "prof.Conservative": ("Conservative", "Prudente"),
    "prof.Moderate": ("Moderate", "Moderato"),
    "prof.Aggressive": ("Aggressive", "Aggressivo"),
    # ---------------------------------------------------------------- app chrome
    "app.disclaimer": (
        "Information tool only, not financial advice. The analyses describe "
        "measurable characteristics of the portfolio based on historical data and "
        "do not constitute personalized investment recommendations, investment "
        "research or forecasts. Past performance is not a reliable indicator of "
        "future results. Figures are gross of costs, fees and taxes; data from "
        "Yahoo Finance, accuracy not guaranteed. No solicitation to buy or sell "
        "financial instruments. Decisions remain with the user or their advisor.",
        "Strumento informativo, non consulenza finanziaria. Le analisi descrivono "
        "caratteristiche misurabili del portafoglio sulla base di dati storici e "
        "non costituiscono raccomandazioni personalizzate di investimento, ricerca "
        "in materia di investimenti né previsioni. I rendimenti passati non sono "
        "un indicatore affidabile dei risultati futuri. I valori sono al lordo di "
        "costi, commissioni e imposte; dati Yahoo Finance, accuratezza non "
        "garantita. Nessuna sollecitazione all'acquisto o alla vendita di "
        "strumenti finanziari. Le decisioni restano all'utente o al suo consulente.",
    ),
    "app.empty_title": ("No portfolio to analyze", "Nessun portafoglio da analizzare"),
    "app.empty_hint": (
        "Add a stock with its amount in the sidebar, "
        "import a broker CSV or load a saved portfolio.",
        "Aggiungi un titolo con il suo importo dalla barra laterale, "
        "importa un CSV del broker o carica un portafoglio salvato.",
    ),
    "top.eur": ("EUR · currency included", "EUR · cambio incluso"),
    "top.orig": ("original currencies", "valute originali"),
    "top.source": ("price source", "fonte prezzi"),
    "nav.checkup": ("Check-up", "Check-up"),
    "nav.analysis": ("Analysis", "Analisi"),
    "nav.strategies": ("Strategies", "Strategie"),
    "nav.market": ("Market", "Mercato"),
    "nav.clients": ("Clients", "Clienti"),
    "nav.metrics": ("Metrics", "Metriche"),
    "nav.charts": ("Charts", "Grafici"),
    "nav.optimization": ("Optimization", "Ottimizzazione"),
    "nav.backtest": ("Backtest", "Backtest"),
    "nav.nasdaq": ("Nasdaq-100", "Nasdaq-100"),
    "nav.correlations": ("Correlations", "Correlazioni"),
    "nav.fundamentals": ("Fundamentals", "Fondamentali"),
    # ---------------------------------------------------------------- gate
    "gate.step": ("Step 1 of 2 · Build your portfolio", "Passo 1 di 2 · Componi il portafoglio"),
    "gate.title": ("Which stocks do you hold?", "Quali titoli possiedi?"),
    "gate.sub": (
        "Add each position with the amount you have invested. "
        "Nothing else is available until you tell us what to analyze.",
        "Aggiungi ogni posizione con l'importo investito. "
        "Il resto si sblocca solo quando ci dici cosa analizzare.",
    ),
    "gate.search_placeholder": (
        "Search by symbol (e.g. AAPL)...",
        "Cerca per simbolo (es. AAPL)...",
    ),
    "gate.add": ("＋ Add", "＋ Aggiungi"),
    "gate.your_holdings": ("Your holdings", "Le tue posizioni"),
    "gate.total": ("Total: **{total}** · {n} stocks", "Totale: **{total}** · {n} titoli"),
    "gate.search_hint": (
        "Search a stock above and add it with its amount.",
        "Cerca un titolo qui sopra e aggiungilo con il suo importo.",
    ),
    "gate.sample": (
        "Try a sample portfolio (AAPL · MSFT · NVDA)",
        "Prova un portafoglio di esempio (AAPL · MSFT · NVDA)",
    ),
    "gate.analyze": ("Analyze my portfolio →", "Analizza il mio portafoglio →"),
    "gate.loading_hint": (
        "Crunching the numbers on your portfolio…",
        "Stiamo macinando i numeri del tuo portafoglio…",
    ),
    # ---------------------------------------------------------------- sidebar
    "side.advisor": ("Advisor: **{advisor}**", "Consulente: **{advisor}**"),
    "side.advisor_demo": (
        "Advisor: **{advisor}** · demo mode",
        "Consulente: **{advisor}** · modalità demo",
    ),
    "side.login_hint": ("Sign in to load your client book.", "Accedi per caricare il tuo book clienti."),
    "side.login": ("Log in", "Accedi"),
    "side.logout": ("Log out", "Esci"),
    "side.add_stock": ("Add a stock", "Aggiungi un titolo"),
    "side.search_hint": (
        "Search a stock to see its name and price, then add it.",
        "Cerca un titolo per vederne nome e prezzo, poi aggiungilo.",
    ),
    "side.your_holdings": ("Your holdings", "Le tue posizioni"),
    "side.amount": ("Amount (€)", "Importo (€)"),
    "side.save": ("Save", "Salva"),
    "side.remove": ("Remove", "Rimuovi"),
    "side.empty_title": ("Empty portfolio", "Portafoglio vuoto"),
    "side.empty_hint": (
        "Search a stock above and add it with its amount.",
        "Cerca un titolo qui sopra e aggiungilo con il suo importo.",
    ),
    "side.import": ("Import from CSV / Excel", "Importa da CSV / Excel"),
    "side.upload_label": (
        "Securities position in CSV or Excel",
        "Posizione titoli in CSV o Excel",
    ),
    "side.upload_help": (
        "Export your broker's SECURITIES POSITION (also called holdings "
        "or portfolio), not the account transactions statement. "
        "Supported formats: CSV and Excel — PDFs are not readable. "
        "Expected columns: ticker/symbol and amount/value, or quantity and price.",
        "Esporta la POSIZIONE TITOLI del tuo broker (detta anche dossier o "
        "portafoglio), non l'estratto conto movimenti. Formati supportati: "
        "CSV ed Excel — i PDF non sono leggibili. Colonne attese: "
        "ticker/simbolo e importo/controvalore, oppure quantità e prezzo.",
    ),
    "side.imported": ("Imported {n} positions", "Importate {n} posizioni"),
    "side.import_failed": ("Import failed: {err}", "Import non riuscito: {err}"),
    "side.saved_portfolios": ("Saved portfolios", "Portafogli salvati"),
    "side.name": ("Name", "Nome"),
    "side.save_composition": ("Save current composition", "Salva la composizione attuale"),
    "side.saved_toast": ('Portfolio "{name}" saved', 'Portafoglio "{name}" salvato'),
    "side.load": ("Load", "Carica"),
    "side.load_placeholder": ("Choose a portfolio...", "Scegli un portafoglio..."),
    "side.load_btn": ("Load into portfolio", "Carica nel portafoglio"),
    "side.settings": ("Settings", "Impostazioni"),
    "side.language": ("Language / Lingua", "Lingua / Language"),
    "side.horizon": ("Historical horizon", "Orizzonte storico"),
    "side.in_eur": ("Measure everything in euros", "Misura tutto in euro"),
    "side.in_eur_help": (
        "US stocks trade in dollars: converting to EUR makes the metrics "
        "include EUR/USD swings too — the real risk for a European investor.",
        "I titoli USA quotano in dollari: convertire in EUR fa includere alle "
        "metriche anche le oscillazioni EUR/USD — il rischio reale per un "
        "investitore europeo.",
    ),
    "side.risk_free": ("Annual risk-free rate (%)", "Tasso privo di rischio annuo (%)"),
    "side.risk_free_help": (
        "Baseline = current US 3-month T-bill (^IRX), fetched live and "
        "editable. Used in Sharpe, Sortino and optimization. Using 0 would "
        "overstate these ratios.",
        "Base = T-bill USA a 3 mesi (^IRX) corrente, scaricato live e "
        "modificabile. Usato in Sharpe, Sortino e ottimizzazione. Usare 0 "
        "gonfierebbe questi indici.",
    ),
    "side.risk_free_caption": (
        "Baseline ^IRX (3M T-bill): {rate}%",
        "Base ^IRX (T-bill 3M): {rate}%",
    ),
    "side.risk_profile": ("Risk profile", "Profilo di rischio"),
    "side.risk_profile_help": (
        "Declared expected annual volatility thresholds: conservative up to "
        "10%, moderate up to 18%, aggressive up to 30%. The check-up "
        "compares the portfolio with the profile threshold.",
        "Soglie di volatilità annua attesa dichiarate: prudente fino al 10%, "
        "moderato fino al 18%, aggressivo fino al 30%. Il check-up confronta "
        "il portafoglio con la soglia del profilo.",
    ),
    # ---------------------------------------------------------------- check-up
    "chk.health_caption": (
        "Health Score: the average of six components — diversification, "
        "concentration, volatility, currency exposure, drawdown, "
        "balance-sheet quality.",
        "Health Score: la media di sei componenti — diversificazione, "
        "concentrazione, volatilità, esposizione valutaria, drawdown, "
        "qualità dei bilanci.",
    ),
    "chk.capital_section": ("Capital over time ({period})", "Capitale nel tempo ({period})"),
    "chk.capital_caption": (
        "Dashed line = capital invested today, projected backwards.",
        "Linea tratteggiata = capitale investito oggi, proiettato all'indietro.",
    ),
    "chk.exec_section": ("Executive summary", "Sintesi esecutiva"),
    "chk.exec_caption": (
        "Summary generated by deterministic rules on the computed metrics: no invented text.",
        "Sintesi generata da regole deterministiche sulle metriche calcolate: "
        "nessun testo inventato.",
    ),
    "chk.holdings": ("Your holdings", "Le tue posizioni"),
    "chk.col_ticker": ("Ticker", "Ticker"),
    "chk.col_company": ("Company", "Società"),
    "chk.col_amount": ("Amount", "Importo"),
    "chk.col_weight": ("Weight", "Peso"),
    "chk.col_today": ("Last session", "Ultima seduta"),
    "chk.col_return": ("Return ({period})", "Rendimento ({period})"),
    "chk.col_trend": ("Trend ({period})", "Andamento ({period})"),
    "chk.top_problems": ("Top problems", "Problemi principali"),
    "chk.profile_problem": (
        "For a **{profile}** profile (expected volatility up to {band}), "
        "the portfolio swings **{excess} more** than the threshold.",
        "Per un profilo **{profile}** (volatilità attesa fino a {band}), il "
        "portafoglio oscilla **{excess} in più** della soglia.",
    ),
    "chk.no_problems": (
        "No problems flagged by the monitored rules.",
        "Nessun problema segnalato dalle regole monitorate.",
    ),
    "chk.risk_eur": ("Your risk, in euros", "Il tuo rischio, in euro"),
    "chk.kpi_swing": ("Typical 1-year swing", "Oscillazione tipica a 1 anno"),
    "chk.kpi_swing_sub": ("{vol} per year · ", "{vol} all'anno · "),
    "chk.kpi_var": ("On a bad day (95% VaR)", "In una giornata storta (VaR 95%)"),
    "chk.kpi_var_sub": (
        "on 95% of days you don't lose more than this (historical estimate)",
        "nel 95% delle giornate non perdi più di così (stima storica)",
    ),
    "chk.kpi_dd": ("In the worst drop of the period", "Nel peggior calo del periodo"),
    "chk.kpi_dd_sub": (
        "{dd} from the peak (max drawdown) investing this amount",
        "{dd} dal massimo (max drawdown) investendo questo importo",
    ),
    "chk.estimates_caption": (
        "Estimates from the period's historical performance: not a forecast.",
        "Stime dall'andamento storico del periodo: non una previsione.",
    ),
    "chk.scenarios": ("Scenarios on your data", "Scenari sui tuoi dati"),
    "chk.halve": (
        "Halve {ticker} (redistributing to the others)",
        "Dimezza {ticker} (redistribuendo sugli altri)",
    ),
    "chk.equalize": ("Equal-weight all holdings", "Equipesa tutte le posizioni"),
    "chk.sim_text": (
        "**{name}**: annual swing from ± {vol_from} to ± {vol_to}, "
        "Health Score from {h_from} to **{h_to}**.",
        "**{name}**: oscillazione annua da ± {vol_from} a ± {vol_to}, "
        "Health Score da {h_from} a **{h_to}**.",
    ),
    "chk.no_improve": (
        "We simulated the most obvious moves on your data, but **none "
        "improves the current profile** — a good sign for how you're weighted:",
        "Abbiamo simulato le mosse più ovvie sui tuoi dati, ma **nessuna "
        "migliora il profilo attuale** — un buon segno per come sei pesato:",
    ),
    "chk.discarded": ("Discarded: ", "Scartata: "),
    "chk.no_scenario": (
        "No scenario proposed: the weights are already well distributed.",
        "Nessuno scenario proposto: i pesi sono già ben distribuiti.",
    ),
    "chk.pdf_btn": ("Download PDF report", "Scarica report PDF"),
    "chk.save_btn": ("Save to history", "Salva nello storico"),
    "chk.saved_toast": ("Analysis saved", "Analisi salvata"),
    "chk.history": ("Analysis history ({n})", "Storico analisi ({n})"),
    "chk.history_caption": (
        'Health Score of "{name}" over time: {delta} points since the first saved analysis.',
        'Health Score di "{name}" nel tempo: {delta} punti dalla prima analisi salvata.',
    ),
    "chk.hist_date": ("Date", "Data"),
    "chk.hist_portfolio": ("Portfolio", "Portafoglio"),
    "chk.hist_period": ("Period", "Periodo"),
    "chk.hist_invested": ("Invested", "Investito"),
    "chk.hist_return": ("Return", "Rendimento"),
    # ---------------------------------------------------------------- metric rows (PDF)
    "m.return": ("Return ({period})", "Rendimento ({period})"),
    "m.cagr": ("Annualized return (CAGR)", "Rendimento annualizzato (CAGR)"),
    "m.vol": ("Annual volatility", "Volatilità annua"),
    "m.sharpe": ("Sharpe ratio", "Sharpe ratio"),
    "m.sortino": ("Sortino ratio", "Sortino ratio"),
    "m.maxdd": ("Max drawdown", "Max drawdown"),
    "m.var": ("VaR 95% (1 day)", "VaR 95% (1 giorno)"),
    "m.es": ("Expected shortfall 95%", "Expected shortfall 95%"),
    "m.beta": ("Beta vs {benchmark}", "Beta vs {benchmark}"),
    "m.alpha": ("Alpha vs {benchmark}", "Alpha vs {benchmark}"),
    "m.corr": ("Average correlation", "Correlazione media"),
    "r.return": (
        "Total change over the observation window, computed on adjusted "
        "prices (dividends and splits included).",
        "Variazione totale nella finestra di osservazione, calcolata su prezzi "
        "rettificati (dividendi e frazionamenti inclusi).",
    ),
    "r.cagr": (
        "Compound annual growth actually earned over the period — geometric, "
        "so volatility does not inflate it.",
        "Crescita annua composta effettivamente maturata nel periodo — "
        "geometrica, quindi la volatilità non la gonfia.",
    ),
    "r.var": (
        "On 95% of days you did not lose more than {amount} "
        "(historical percentile, no normality assumed).",
        "Nel 95% delle giornate non hai perso più di {amount} "
        "(percentile storico, nessuna ipotesi di normalità).",
    ),
    "r.es": (
        "Average loss on the worst 5% of days ({amount}): what a bad "
        "day costs when it goes beyond the VaR threshold.",
        "Perdita media nel 5% di giornate peggiori ({amount}): quanto costa "
        "una giornata storta quando supera la soglia del VaR.",
    ),
    "r.alpha": (
        "Annual excess return not explained by benchmark moves (OLS on daily data).",
        "Extra-rendimento annuo non spiegato dai movimenti del benchmark "
        "(OLS su dati giornalieri).",
    ),
    "suit.text": (
        "Observed annual volatility {vol} vs the {band} threshold declared "
        "for a {profile} profile.",
        "Volatilità annua osservata {vol} contro la soglia {band} dichiarata "
        "per un profilo {profile}.",
    ),
    "scen.label": (
        "{ticker} (your largest position, {weight} of capital) drops 20%",
        "{ticker} (la tua posizione più grande, {weight} del capitale) perde il 20%",
    ),
    "cov.note": (
        "{ticker} priced only from {date} — its metrics use the shorter overlap",
        "{ticker} quotato solo dal {date} — le sue metriche usano la "
        "sovrapposizione più corta",
    ),
    "pdf.currency_eur": (
        "amounts in EUR, currency effect included",
        "importi in EUR, effetto cambio incluso",
    ),
    "pdf.currency_orig": (
        "amounts in original currencies",
        "importi nelle valute originali",
    ),
    # ---------------------------------------------------------------- PDF statics
    "pdf.doc_title": ("SmarteeFinance — Portfolio Report", "SmarteeFinance — Report di Portafoglio"),
    "pdf.title": ("Portfolio Report", "Report di Portafoglio"),
    "pdf.prepared_by": ("prepared by {advisor}", "predisposto da {advisor}"),
    "pdf.profile": ("{profile} profile", "profilo {profile}"),
    "pdf.window": (
        "observation window {start} – {end}",
        "finestra di osservazione {start} – {end}",
    ),
    "pdf.generated": ("generated on {now}", "generato il {now}"),
    "pdf.kpi_health": ("HEALTH SCORE", "HEALTH SCORE"),
    "pdf.kpi_value": ("ESTIMATED VALUE", "VALORE STIMATO"),
    "pdf.kpi_return": ("RETURN ({period})", "RENDIMENTO ({period})"),
    "pdf.kpi_cagr": ("CAGR", "CAGR"),
    "pdf.kpi_invested": ("INVESTED", "INVESTITO"),
    "pdf.exec_summary": ("Executive summary", "Sintesi esecutiva"),
    "pdf.no_summary": (
        "Summary not available for this analysis.",
        "Sintesi non disponibile per questa analisi.",
    ),
    "pdf.check_title": ("Risk profile check", "Verifica del profilo di rischio"),
    "pdf.within": ("within", "entro"),
    "pdf.outside": ("OUTSIDE", "FUORI DA"),
    "pdf.check_text": (
        "<b>Risk profile check — {status} the declared profile.</b> {text} ",
        "<b>Verifica del profilo di rischio — {status} il profilo dichiarato.</b> {text} ",
    ),
    "pdf.check_caveat": (
        "Volatility-only software check: it does not replace the MiFID II "
        "suitability assessment, which remains the responsibility of the advisor.",
        "Verifica software sulla sola volatilità: non sostituisce la "
        "valutazione di adeguatezza MiFID II, che resta responsabilità del consulente.",
    ),
    "pdf.capital_section": (
        "Capital over time ({period}) vs {benchmark}",
        "Capitale nel tempo ({period}) vs {benchmark}",
    ),
    "pdf.capital_caption": (
        "Dotted line = capital invested today, projected backwards. "
        "Benchmark: {benchmark} rebased to the same starting capital.",
        "Linea punteggiata = capitale investito oggi, proiettato all'indietro. "
        "Benchmark: {benchmark} ribasato sullo stesso capitale iniziale.",
    ),
    "pdf.no_history": ("Price history not available.", "Storico prezzi non disponibile."),
    "pdf.holdings": ("Holdings", "Posizioni"),
    "pdf.h_ticker": ("Ticker", "Ticker"),
    "pdf.h_company": ("Company", "Società"),
    "pdf.h_amount": ("Amount", "Importo"),
    "pdf.h_weight": ("Weight", "Peso"),
    "pdf.h_return": ("Return ({period})", "Rendimento ({period})"),
    "pdf.h_risk": ("Risk share", "Quota rischio"),
    "pdf.other_holdings": ("other holdings", "altre posizioni"),
    "pdf.coverage": ("Data coverage: ", "Copertura dati: "),
    "pdf.portfolio_legend": ("Portfolio", "Portafoglio"),
    "pdf.benchmark_legend": ("{benchmark} benchmark", "benchmark {benchmark}"),
    "pdf.trough": ("trough {dd} on {date}", "minimo {dd} il {date}"),
    "pdf.p2_title": ("Risk & performance analytics", "Analisi di rischio e performance"),
    "pdf.metrics_section": (
        "Metrics, portfolio vs {benchmark}, and how to read them",
        "Metriche, portafoglio vs {benchmark}, e come leggerle",
    ),
    "pdf.h_metric": ("Metric", "Metrica"),
    "pdf.h_portfolio": ("Portfolio", "Portafoglio"),
    "pdf.h_reading": ("Reading", "Lettura"),
    "pdf.underwater_title": (
        "Distance from the peak (underwater)",
        "Distanza dal massimo (underwater)",
    ),
    "pdf.monthly_title": (
        "Monthly returns (last 12 months)",
        "Rendimenti mensili (ultimi 12 mesi)",
    ),
    "pdf.breakdown_section": (
        "Health Score: the six components",
        "Health Score: le sei componenti",
    ),
    "pdf.breakdown_caption": (
        "0-100 per component; the Health Score is their average. "
        "Green ≥ 67, amber 34-66, red ≤ 33.",
        "0-100 per componente; l'Health Score è la loro media. "
        "Verde ≥ 67, ambra 34-66, rosso ≤ 33.",
    ),
    "pdf.no_breakdown": (
        "Component breakdown not available.",
        "Scomposizione per componenti non disponibile.",
    ),
    "pdf.p3_title": (
        "Diversification, scenarios & observations",
        "Diversificazione, scenari e osservazioni",
    ),
    "pdf.wr_title": ("Weight vs risk contribution", "Peso vs contributo al rischio"),
    "pdf.wr_caption": (
        "Risk share = contribution to portfolio variance (covariances "
        "included). A holding whose risk share far exceeds its weight "
        "dominates the swings.",
        "Quota rischio = contributo alla varianza di portafoglio (covarianze "
        "incluse). Una posizione con quota rischio molto oltre il peso domina "
        "le oscillazioni.",
    ),
    "pdf.legend_weight": ("capital weight", "peso sul capitale"),
    "pdf.legend_risk": ("share of portfolio risk", "quota del rischio di portafoglio"),
    "pdf.sector_title": ("Allocation by sector", "Allocazione per settore"),
    "pdf.sector_caption": (
        "Sectors from Yahoo Finance company profiles, weighted by capital.",
        "Settori dai profili societari Yahoo Finance, pesati per capitale.",
    ),
    "pdf.other_sectors": ("Other sectors", "Altri settori"),
    "pdf.not_classified": ("Not classified", "Non classificato"),
    "pdf.no_risk_decomp": (
        "Risk decomposition not available.",
        "Scomposizione del rischio non disponibile.",
    ),
    "pdf.c_holdings": ("HOLDINGS", "POSIZIONI"),
    "pdf.c_effective": ("EFFECTIVE HOLDINGS", "POSIZIONI EFFETTIVE"),
    "pdf.c_top": ("TOP POSITION", "POSIZIONE MAGGIORE"),
    "pdf.c_hhi": ("CONCENTRATION (HHI)", "CONCENTRAZIONE (HHI)"),
    "pdf.conc_caption": (
        "Effective holdings = 1/HHI: how many equally-weighted positions your "
        "concentration is equivalent to.",
        "Posizioni effettive = 1/HHI: a quante posizioni equipesate equivale "
        "la tua concentrazione.",
    ),
    "pdf.stress_title": ("Stress scenario on your data", "Scenario di stress sui tuoi dati"),
    "pdf.stress_text": (
        "If <b>{label}</b>, the direct hit on the portfolio is <b>{direct}</b> "
        "({direct_eur}); including the historical co-movement of the other "
        "holdings, the estimated total impact is <b>{total}</b> ({total_eur}).",
        "Se <b>{label}</b>, l'impatto diretto sul portafoglio è <b>{direct}</b> "
        "({direct_eur}); includendo il co-movimento storico delle altre "
        "posizioni, l'impatto totale stimato è <b>{total}</b> ({total_eur}).",
    ),
    "pdf.stress_caption": (
        "Contagion estimated from each holding's historical beta to the shocked "
        "position over the selected period. An estimate, not a forecast.",
        "Contagio stimato dai beta storici di ogni posizione verso il titolo "
        "colpito nel periodo selezionato. Una stima, non una previsione.",
    ),
    "pdf.no_scenario": (
        "No stress scenario computed for this portfolio.",
        "Nessuno scenario di stress calcolato per questo portafoglio.",
    ),
    "pdf.attention_title": ("Points of attention", "Punti di attenzione"),
    "pdf.none_flagged": (
        "Nothing flagged by the monitored rules.",
        "Nulla da segnalare secondo le regole monitorate.",
    ),
    "pdf.obs_title": ("Observations & talking points", "Osservazioni e spunti di confronto"),
    "pdf.obs_caption": (
        "Generated by deterministic rules on the computed metrics — not personalized "
        "investment advice: material for the review with the advisor.",
        "Generati da regole deterministiche sulle metriche calcolate — non "
        "consulenza personalizzata: materiale per il confronto col consulente.",
    ),
    "pdf.notices_title": (
        "Methodology, assumptions & important notices",
        "Metodologia, assunzioni e avvertenze importanti",
    ),
    "pdf.notice_caution": (
        "CAUTION: the observation window is shorter than one year — annualized "
        "figures (CAGR, volatility, Sharpe/Sortino) extrapolate from few months "
        "and should be read as indicative only.",
        "ATTENZIONE: la finestra di osservazione è inferiore a un anno — i "
        "valori annualizzati (CAGR, volatilità, Sharpe/Sortino) estrapolano da "
        "pochi mesi e vanno letti come puramente indicativi.",
    ),
    "pdf.notice_data": (
        "Data: Yahoo Finance daily adjusted closes over the selected period "
        "({period}), converted to EUR where noted; dividends and splits are "
        "incorporated in returns via price adjustment. Data are provided "
        "as-is: accuracy, completeness and timeliness are not guaranteed.",
        "Dati: chiusure giornaliere rettificate Yahoo Finance nel periodo "
        "selezionato ({period}), convertite in EUR dove indicato; dividendi e "
        "frazionamenti sono incorporati nei rendimenti tramite la rettifica dei "
        "prezzi. Dati forniti così come sono: accuratezza, completezza e "
        "tempestività non garantite.",
    ),
    "pdf.notice_costs": (
        "All figures are gross of transaction costs, management fees and "
        "taxes, which would reduce the results shown.",
        "Tutti i valori sono al lordo di costi di transazione, commissioni di "
        "gestione e imposte, che ridurrebbero i risultati mostrati.",
    ),
    "pdf.notice_returns": (
        "Returns are geometric (CAGR) — never arithmetic-mean annualization, "
        "which overstates results under volatility. Sharpe/Sortino: excess "
        "return over the risk-free rate{rf}; Sortino penalizes downside "
        "deviation only.",
        "I rendimenti sono geometrici (CAGR) — mai annualizzazione a media "
        "aritmetica, che gonfia i risultati in presenza di volatilità. "
        "Sharpe/Sortino: extra-rendimento sul tasso privo di rischio{rf}; il "
        "Sortino penalizza la sola deviazione al ribasso.",
    ),
    "pdf.notice_rf": (
        " ({rate}, 3-month US T-bill ^IRX)",
        " ({rate}, T-bill USA a 3 mesi ^IRX)",
    ),
    "pdf.notice_var": (
        "VaR 95%: historical 5th percentile of daily returns, no normality "
        "assumed; expected shortfall = average of the tail beyond it. "
        "Beta/alpha: OLS regression of daily portfolio returns on {benchmark}. "
        "Risk contributions: share of portfolio variance per holding, "
        "covariances included.",
        "VaR 95%: 5° percentile storico dei rendimenti giornalieri, nessuna "
        "ipotesi di normalità; expected shortfall = media della coda oltre la "
        "soglia. Beta/alpha: regressione OLS dei rendimenti giornalieri del "
        "portafoglio su {benchmark}. Contributi al rischio: quota della "
        "varianza di portafoglio per posizione, covarianze incluse.",
    ),
    "pdf.notice_estimates": (
        "All figures describe the observed period only: they are estimates, "
        "not forecasts. Past performance is not a reliable indicator of "
        "future results.",
        "Tutti i valori descrivono il solo periodo osservato: sono stime, non "
        "previsioni. I rendimenti passati non sono un indicatore affidabile "
        "dei risultati futuri.",
    ),
    "pdf.notice_no_advice": (
        "This document is a statistical analysis generated by SmarteeFinance "
        "software. It does not constitute investment advice, a personalized "
        "recommendation, investment research, or an offer or solicitation to "
        "buy or sell any financial instrument.",
        "Questo documento è un'analisi statistica generata dal software "
        "SmarteeFinance. Non costituisce consulenza in materia di "
        "investimenti, raccomandazione personalizzata, ricerca in materia di "
        "investimenti, né offerta o sollecitazione all'acquisto o alla vendita "
        "di alcuno strumento finanziario.",
    ),
    "pdf.notice_profile": (
        "The risk profile check compares observed volatility with the "
        "threshold of the declared profile only: it is not the MiFID II "
        "suitability or appropriateness assessment, which remains the "
        "responsibility of the licensed advisor.",
        "La verifica del profilo di rischio confronta la sola volatilità "
        "osservata con la soglia del profilo dichiarato: non è la valutazione "
        "di adeguatezza o appropriatezza MiFID II, che resta responsabilità "
        "del consulente abilitato.",
    ),
    "pdf.notice_confidential": (
        "Prepared exclusively for the named recipient as working material for "
        "the advisory relationship; not intended for public distribution.",
        "Predisposto esclusivamente per il destinatario indicato come "
        "materiale di lavoro del rapporto di consulenza; non destinato alla "
        "distribuzione al pubblico.",
    ),
    "pdf.footer_line1": (
        "SmarteeFinance · Portfolio Intelligence · Ref. {rid} · Yahoo Finance "
        "data, accuracy and completeness not guaranteed",
        "SmarteeFinance · Portfolio Intelligence · Rif. {rid} · dati Yahoo "
        "Finance, accuratezza e completezza non garantite",
    ),
    "pdf.footer_line2": (
        "Past performance is not a reliable indicator of future results. This "
        "document is not investment advice, investment research, an offer or "
        "a solicitation.",
        "I rendimenti passati non sono un indicatore affidabile dei risultati "
        "futuri. Questo documento non è consulenza in materia di investimenti, "
        "ricerca, offerta né sollecitazione.",
    ),
    "pdf.page": ("Page {n} of 3", "Pagina {n} di 3"),
    # ---------------------------------------------------------------- components
    "hero.value": ("Estimated value", "Valore stimato"),
    "hero.last_session": ("Last session", "Ultima seduta"),
    "hero.score_built": ("HOW THE SCORE IS BUILT", "COME NASCE IL PUNTEGGIO"),
    "hero.dna_title": ("PORTFOLIO DNA", "DNA DEL PORTAFOGLIO"),
}
