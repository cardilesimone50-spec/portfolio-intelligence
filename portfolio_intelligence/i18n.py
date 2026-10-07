"""Catalogo bilingue EN/IT e stato lingua dell'app.

Uso: `t(key, **kwargs)` traduce nella lingua corrente (default inglese, così
i test restano stabili); `t_in(lang, key, **kwargs)` traduce in una lingua
esplicita (usato dal PDF, che riceve `lang` come parametro).
Ogni voce del catalogo è (inglese, italiano); chiave mancante → torna la chiave.
"""

from contextvars import ContextVar

_EN, _IT = 0, 1
LANGUAGES = {"en": "English", "it": "Italiano"}
# Lingua per esecuzione, non per processo: Streamlit esegue ogni sessione nel
# proprio thread e una variabile globale farebbe leggere a un utente la lingua
# scelta da un altro. Un thread nuovo parte dal default inglese.
_LANG: ContextVar[str] = ContextVar("language", default="en")


def set_language(lang: str) -> None:
    _LANG.set(lang if lang in LANGUAGES else "en")


def get_language() -> str:
    return _LANG.get()


def t(key: str, **kwargs) -> str:
    return t_in(_LANG.get(), key, **kwargs)


def period_text(code: str) -> str:
    """Orizzonte leggibile nella lingua corrente ("1 anno"); il codice se sconosciuto."""
    key = f"period.{code}"
    return t(key) if key in _CATALOG else code


def sector_text(name):
    """Nome di settore nella lingua corrente; invariato se non in catalogo o vuoto."""
    if not isinstance(name, str) or not name:
        return name
    key = f"sector.{name}"
    return t(key) if key in _CATALOG else name


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
        "Negative risk-adjusted return: over the period the portfolio returned "
        "less than the risk-free rate.",
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
        "Above the 0.5-1 range historically typical of diversified equity.",
        "Sopra la banda 0,5-1 storicamente tipica dell'azionario diversificato.",
    ),
    "sharpe.exceptional": (
        "Exceptional over the observed period: such values rarely persist.",
        "Eccezionale nel periodo osservato: valori simili raramente persistono.",
    ),
    "sortino.upside": (
        "Return dispersion skewed to the upside: downside deviation is lower than total volatility implies.",
        "Dispersione dei rendimenti sbilanciata al rialzo: la deviazione al ribasso è inferiore a quanto implica la volatilità totale.",
    ),
    "sortino.downside": (
        "Return dispersion skewed to the downside: losses dominate total volatility.",
        "Dispersione dei rendimenti sbilanciata al ribasso: le perdite dominano la volatilità totale.",
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
        "Bear-market magnitude (beyond -20%).",
        "Ampiezza da mercato ribassista (oltre il -20%).",
    ),
    "dd.severe": (
        "Severe drawdown (beyond -35%): a full recovery requires a gain of more than 50%.",
        "Drawdown severo (oltre il -35%): il pieno recupero richiede un guadagno superiore al 50%.",
    ),
    "beta.defensive": (
        "More defensive than {benchmark}: benchmark moves are dampened.",
        "Più difensivo del benchmark {benchmark}: i movimenti di mercato vengono attutiti.",
    ),
    "beta.inline": (
        "Broadly in line with {benchmark}.",
        "Il portafoglio si muove sostanzialmente in linea col benchmark {benchmark}.",
    ),
    "beta.amplify": (
        "Amplifies {benchmark} moves: steeper rises and falls.",
        "I movimenti del benchmark {benchmark} vengono amplificati: salite e discese più ripide.",
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
        "Over the last {period}, with current weights, the portfolio returned {ret}.",
        "Nell'ultimo periodo ({period}), a pesi attuali, il portafoglio ha reso {ret}.",
    ),
    "exec.corr_weak": (
        "Diversification is weak: the holdings move very similarly (average correlation {corr}).",
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
        "Maximum drawdown over the period {dd}, beyond the 25% reference level.",
        "Massimo drawdown nel periodo {dd}, oltre il livello di riferimento del 25%.",
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
        "Con un beta di {beta} verso {benchmark}, il portafoglio è più difensivo del mercato.",
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
        "Average pairwise correlation **{corr}**: limited diversification across holdings.",
        "Correlazione media tra coppie **{corr}**: diversificazione limitata tra i titoli.",
    ),
    "prob.dividend": (
        "Weighted dividend yield **{dy}%**, below the 1% reference level.",
        "Rendimento da dividendi ponderato **{dy}%**, sotto il livello di riferimento dell'1%.",
    ),
    "prob.volatility": (
        "Volatility score in the top band of the scale used (above 70 out of 100).",
        "Punteggio di volatilità nella fascia alta della scala usata (oltre 70 su 100).",
    ),
    # ---------------------------------------------------------------- opportunities
    "opp.defensive_sectors": (
        "No exposure to the defensive sectors monitored (**{sectors}**).",
        "Nessuna esposizione ai settori difensivi monitorati (**{sectors}**).",
    ),
    "opp.cheap": (
        "**{ticker}** has trailing P/E {pe} and P/S {ps}, below the 25 and 6 reference levels.",
        "**{ticker}** ha P/E storico {pe} e P/S {ps}, sotto i livelli di riferimento di 25 e 6.",
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
        "Holdings are tightly linked (average correlation **{corr}**): diversification is weak.",
        "I titoli sono strettamente legati (correlazione media **{corr}**): "
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
        "Beta **{beta}** vs {benchmark}: market moves are amplified.",
        "Beta **{beta}** vs {benchmark}: i movimenti di mercato vengono amplificati.",
    ),
    "ins.beta_low": (
        "Beta **{beta}** vs {benchmark}: more defensive than the market.",
        "Beta **{beta}** vs {benchmark}: più difensivo del mercato.",
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
    "investor.disclaimer": (
        "Informational portfolio-analysis tool. It does not constitute "
        "personalized financial advice under Italian law (TUF).",
        "Strumento informativo di analisi del portafoglio. Non costituisce "
        "consulenza finanziaria personalizzata ai sensi del TUF.",
    ),
    "app.disclaimer": (
        "Information tool only, not financial advice. The analyses describe "
        "measurable characteristics of the portfolio based on historical data and "
        "do not constitute personalized investment recommendations, investment "
        "research or forecasts. Past performance is not a reliable indicator of "
        "future results. Figures are gross of costs, fees and taxes; market data "
        "from third-party providers, accuracy not guaranteed. No solicitation to buy or sell "
        "financial instruments. Decisions remain with the user or their advisor.",
        "Strumento informativo, non consulenza finanziaria. Le analisi descrivono "
        "caratteristiche misurabili del portafoglio sulla base di dati storici e "
        "non costituiscono raccomandazioni personalizzate di investimento, ricerca "
        "in materia di investimenti né previsioni. I rendimenti passati non sono "
        "un indicatore affidabile dei risultati futuri. I valori sono al lordo di "
        "costi, commissioni e imposte; dati di mercato da fornitori terzi, "
        "accuratezza non garantita. Nessuna sollecitazione all'acquisto o alla vendita di "
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
    "nav.admin": ("Admin", "Admin"),
    "nav.metrics": ("Metrics", "Metriche"),
    "nav.charts": ("Charts", "Grafici"),
    "nav.optimization": ("Optimization", "Ottimizzazione"),
    "nav.backtest": ("Backtest", "Backtest"),
    "nav.nasdaq": ("Nasdaq-100", "Nasdaq-100"),
    "nav.correlations": ("Correlations", "Correlazioni"),
    "nav.fundamentals": ("Fundamentals", "Fondamentali"),
    # ------------------------------------------------------- profile chooser
    "chooser.title": (
        "Choose how to use Smarteefinance",
        "Scegli come usare Smarteefinance",
    ),
    "chooser.sub": (
        "Investor is a quick check-up of your own portfolio. Advisor is for "
        "professionals who manage client portfolios.",
        "Investor è un check-up rapido del tuo portafoglio. Advisor è per i "
        "professionisti che gestiscono portafogli di clienti.",
    ),
    "chooser.investor_title": ("Explore as Investor", "Esplora come Investor"),
    "chooser.investor_desc": (
        "No sign-up. A portfolio check-up in about a minute, risk measured "
        "in euros, market overview. Your positions stay in the browser "
        "session and are not saved to any database.",
        "Senza registrazione. Check-up del portafoglio in circa un minuto, "
        "rischio misurato in euro, panoramica di mercato. Le posizioni restano "
        "nella sessione del browser e non vengono salvate in alcun database.",
    ),
    "chooser.investor_cta": ("Start as Investor →", "Inizia come Investor →"),
    "chooser.advisor_title": ("Sign in as Advisor", "Accedi come Advisor"),
    "chooser.advisor_desc": (
        "Secure OIDC login, saved client portfolios, multi-tenant analysis "
        "history, admin tools. Built for professional use, data isolated "
        "per advisor.",
        "Login sicuro OIDC, portafogli clienti salvati, storico analisi "
        "multi-tenant, strumenti di amministrazione. Pensato per l'uso "
        "professionale, dati isolati per consulente.",
    ),
    "chooser.advisor_cta": ("Sign in as Advisor →", "Accedi come Advisor →"),
    "chooser.footer": (
        "Not sure which one? Investor costs nothing to try. You can switch anytime "
        "by returning to this page.",
        "Non sai quale scegliere? Investor non costa nulla da provare: puoi cambiare in qualsiasi momento tornando su questa pagina.",
    ),
    # ------------------------------------------------------- advisor welcome
    "advisorw.title": ("Advisor console", "Console Consulenti"),
    "advisorw.sub": (
        "Portfolio monitoring, risk analysis and client reporting for independent advisors, "
        "boutiques and back-office teams.",
        "Monitoraggio dei portafogli, analisi del rischio e reportistica per consulenti "
        "indipendenti, boutique e back office.",
    ),
    "advisorw.badge_sso": ("Sign-in via OIDC", "Accesso tramite OIDC"),
    "advisorw.badge_tenant": ("Data separated per advisor", "Dati separati per consulente"),
    "advisorw.badge_audit": ("Activity log", "Registro delle attività"),
    "advisorw.feature1_title": ("Client book and monitoring", "Book clienti e monitoraggio"),
    "advisorw.feature1_desc": (
        "One row per client, ordered by who needs review, with internal thresholds on "
        "profile volatility, concentration, currency and drawdown. CSV export.",
        "Una riga per cliente, ordinata da chi va rivisto, con soglie interne su volatilità "
        "del profilo, concentrazione, valuta e drawdown. Esportazione CSV.",
    ),
    "advisorw.feature2_title": ("Risk and performance", "Rischio e performance"),
    "advisorw.feature2_desc": (
        "Volatility, VaR, drawdown, Sharpe and beta against the benchmark; Markowitz "
        "optimization, strategy backtests and Monte Carlo projections.",
        "Volatilità, VaR, drawdown, Sharpe e beta contro il benchmark; ottimizzazione di "
        "Markowitz, backtest delle strategie e proiezioni Monte Carlo.",
    ),
    "advisorw.feature3_title": ("Client reporting", "Reportistica per il cliente"),
    "advisorw.feature3_desc": (
        "Portfolio review for the advisor (investment view, benchmark analysis, risk, stress tests, Monte Carlo, suitability context, sign-off) and a four-page report for the client.",
        "Revisione di portafoglio per il consulente (sintesi d'investimento, confronto col benchmark, rischi, stress test, Monte Carlo, contesto di adeguatezza, firme) e report di quattro pagine per il cliente.",
    ),
    "advisorw.feature4_title": ("Data and controls", "Dati e controlli"),
    "advisorw.feature4_desc": (
        "Data separated per advisor, activity log and erasure on request. Fundamentals "
        "from SEC filings, EUR/USD from the ECB, risk-free rate from the US Treasury.",
        "Dati separati per consulente, registro delle attività e cancellazione su "
        "richiesta. Fondamentali dai bilanci SEC, cambio EUR/USD dalla BCE, tasso privo di "
        "rischio dal Tesoro USA.",
    ),
    "advisorw.login_title": ("Sign in", "Accedi"),
    "advisorw.login_cta": (
        "Sign in with SSO / company credentials",
        "Accedi con SSO / credenziali aziendali",
    ),
    "advisorw.login_dev_warning": (
        "Running in dev mode? OIDC isn't configured in this environment. "
        "Configure `[auth]` in secrets.toml to enable real sign-in (see the README).",
        "Sei in modalità Dev? L'OIDC non è configurato in questo ambiente. "
        "Configura `[auth]` in secrets.toml per abilitare il login reale (vedi il README).",
    ),
    "advisorw.login_dev_continue": (
        "Continue without authentication (dev) →",
        "Continua senza autenticazione (dev) →",
    ),
    "app.bench_stored": (
        "Live prices for {benchmark} are unavailable: the comparison uses the stored history, "
        "up to {date}.",
        "Prezzi aggiornati di {benchmark} non disponibili: il confronto usa lo storico "
        "salvato, fino al {date}.",
    ),
    "app.fund_unavailable": (
        "Company financials are temporarily unavailable: risk, return and "
        "diversification are complete, valuation and quality indicators are not.",
        "I dati di bilancio delle società non sono al momento disponibili: rischio, "
        "rendimento e diversificazione sono completi, valutazione e qualità no.",
    ),
    # ---------------------------------------------------------------- data/charts
    "chart.weight": ("Invested weight", "Peso investito"),
    "chart.risk_contribution": ("Risk contribution", "Contributo al rischio"),
    "app.loading_data": ("Loading market data…", "Caricamento dei dati di mercato…"),
    "db.missing_title": (
        "Price database not available yet",
        "Database prezzi non ancora presente",
    ),
    "db.missing_hint": (
        "Five years of daily prices for the 103 Nasdaq-100 stocks and the reference indices "
        "(S&P 500, FTSE MIB, STOXX Europe 600) are needed: downloaded once, then refreshed.",
        "Servono cinque anni di prezzi giornalieri dei 103 titoli del Nasdaq-100 e degli indici "
        "di riferimento (S&P 500, FTSE MIB, STOXX Europe 600): si scaricano una volta, poi si "
        "aggiornano.",
    ),
    "db.download_btn": ("Download data (about one minute)", "Scarica i dati (circa un minuto)"),
    "db.downloading": (
        "Downloading five years of prices…",
        "Download di cinque anni di prezzi in corso…",
    ),
    # ---------------------------------------------------------------- monte carlo
    "nav.montecarlo": ("Monte Carlo", "Monte Carlo"),
    "mc.title": ("Scenario simulation (Monte Carlo)", "Simulazione scenari (Monte Carlo)"),
    "mc.intro": (
        "Thousands of possible paths of the portfolio value, built from its own daily "
        "history: the bands show the range of outcomes, not a target.",
        "Migliaia di traiettorie possibili del valore del portafoglio, costruite dal suo "
        "storico giornaliero: le fasce mostrano l'ampiezza degli esiti, non un obiettivo.",
    ),
    "mc.horizon": ("Horizon", "Orizzonte"),
    "mc.years": ("{n} years", "{n} anni"),
    "mc.method": ("Method", "Metodo"),
    "mc.method_bootstrap": ("Historical bootstrap", "Bootstrap storico"),
    "mc.method_gbm": ("Parametric (GBM)", "Parametrico (GBM)"),
    "mc.simulations": ("Simulations", "Simulazioni"),
    "mc.kpi_median": ("Median value in {years} years", "Valore mediano a {years} anni"),
    "mc.kpi_prudent": ("Prudent value (10th percentile)", "Valore prudenziale (10° percentile)"),
    "mc.kpi_positive": ("Chance of a positive result", "Probabilità di risultato positivo"),
    "mc.kpi_vs_today": (
        "{pct} vs today · {cagr} per year",
        "{pct} rispetto a oggi · {cagr} annuo",
    ),
    "mc.kpi_positive_sub": (
        "95% of scenarios end above {p5}.",
        "Il 95% degli scenari termina sopra {p5}.",
    ),
    "mc.history": (
        "Based on {n} days of joint history ({start} – {end}) · {sims} simulations · "
        "constant weights, no costs, no contributions or withdrawals.",
        "Basata su {n} giorni di storico congiunto ({start} – {end}) · {sims} simulazioni · "
        "pesi costanti, senza costi, versamenti o prelievi.",
    ),
    "mc.short_history": (
        "The history used is shorter than two years: the projection inherits the returns "
        "of a single, possibly exceptional, period. Set a longer historical horizon in "
        "Analysis parameters.",
        "Lo storico usato è più corto di due anni: la proiezione eredita i rendimenti di "
        "un solo periodo, forse eccezionale. Imposta un orizzonte storico più lungo nei "
        "Parametri di analisi.",
    ),
    "mc.unavailable": ("Simulation not available: {err}", "Simulazione non disponibile: {err}"),
    "mc.disclaimer": (
        "Probabilistic projection based on the historical series. It is not a guarantee "
        "of future returns, nor a forecast or an investment recommendation.",
        "Proiezione probabilistica basata sulla serie storica. Non costituisce garanzia "
        "di rendimento futuro, né previsione o raccomandazione di investimento.",
    ),
    "mc.method_title": ("Methodology", "Metodologia"),
    "mc.method_text": (
        "**Historical bootstrap**: each simulated day is a real day of the selected "
        "history for all holdings at once, drawn at random in blocks of five trading "
        "days. Correlations and fat tails stay as they actually were.\n\n"
        "**Parametric (GBM)**: daily log-returns drawn from a normal distribution with "
        "the portfolio's historical geometric growth and its volatility from the "
        "covariance matrix. Smoother than reality: it underestimates extreme days.\n\n"
        "Both use constant weights (daily rebalancing), values in EUR when the analysis "
        "is in EUR, and a fixed random seed, so the same inputs give the same result.",
        "**Bootstrap storico**: ogni giorno simulato è un giorno reale dello storico "
        "selezionato per tutti i titoli insieme, estratto a caso in blocchi di cinque "
        "giorni di borsa. Correlazioni e code grasse restano quelle effettive.\n\n"
        "**Parametrico (GBM)**: log-rendimenti giornalieri estratti da una normale con la "
        "crescita geometrica storica del portafoglio e la volatilità dalla matrice di "
        "covarianza. Più regolare della realtà: sottostima i giorni estremi.\n\n"
        "Entrambi usano pesi costanti (ribilanciamento giornaliero), valori in EUR se "
        "l'analisi è in EUR e un seme casuale fisso: a parità di dati, stesso risultato.",
    ),
    "mc.axis_years": ("Years from today", "Anni da oggi"),
    "mc.month0": ("Today", "Oggi"),
    "mc.when": ("Year {years}, month {months}", "Anno {years}, mese {months}"),
    "mc.tt_when": ("When", "Quando"),
    "mc.tt_p90": ("Optimistic (p90)", "Ottimistico (p90)"),
    "mc.tt_p75": ("p75", "p75"),
    "mc.tt_p50": ("Median (p50)", "Mediano (p50)"),
    "mc.tt_p25": ("p25", "p25"),
    "mc.tt_p10": ("Pessimistic (p10)", "Pessimistico (p10)"),
    "pdf.mc_years": ("{n} yr", "{n} anni"),
    "pdf.mc_year1": ("1 yr", "1 anno"),
    # ---------------------------------------------------------------- area switch
    "area.label": ("Area", "Area"),
    "area.investor": ("Investor", "Investor"),
    "area.advisor": ("Advisor", "Advisor"),
    # ---------------------------------------------------------------- legal
    "legal.privacy": ("Privacy policy", "Informativa privacy"),
    "legal.terms": ("Terms of service", "Termini di servizio"),
    "legal.cookies": ("Cookie policy", "Cookie policy"),
    "legal.imprint": ("Legal notice", "Note legali"),
    "legal.nav_label": ("Legal information", "Informazioni legali"),
    "legal.italian_only": (
        "Legal documents are published in Italian, the authoritative version.",
        "I documenti legali sono pubblicati in italiano, che è la versione di riferimento.",
    ),
    # ---------------------------------------------------------------- advisor workspace
    "adv.product": ("Advisor", "Advisor"),
    "adv.nav_clients": ("Clients", "Clienti"),
    "adv.nav_new": ("New client", "Nuovo cliente"),
    "adv.nav_market": ("Market", "Mercato"),
    "adv.nav_admin": ("Administration", "Amministrazione"),
    "adv.nav_active": ("Active client", "Cliente attivo"),
    "adv.nav_label": ("Advisor navigation", "Navigazione Advisor"),
    "adv.sec_overview": ("Overview", "Panoramica"),
    "adv.sec_positions": ("Positions", "Posizioni"),
    "adv.sec_analysis": ("Analysis", "Analisi"),
    "adv.sec_strategies": ("Strategies", "Strategie"),
    "adv.params": ("Analysis parameters", "Parametri di analisi"),
    "adv.signed_in": ("Signed in as {advisor}", "Accesso come {advisor}"),
    "adv.dev_env": (
        "Development environment: sign-in is not configured.",
        "Ambiente di sviluppo: l'accesso non è configurato.",
    ),
    "adv.clients_title": ("Clients", "Clienti"),
    "adv.clients_sub": (
        "The portfolios you follow, ordered by who needs attention first.",
        "I portafogli che segui, ordinati da chi richiede attenzione per primo.",
    ),
    "adv.kpi_clients": ("Clients", "Clienti"),
    "adv.kpi_aum": ("Assets monitored", "Patrimonio monitorato"),
    "adv.kpi_review": ("To review", "Da rivedere"),
    "adv.kpi_review_sub": (
        "Health Score below {fair} or volatility above the client's profile.",
        "Health Score sotto {fair} o volatilità oltre il profilo del cliente.",
    ),
    "adv.kpi_health": ("Average Health Score", "Health Score medio"),
    "adv.kpi_aum_sub": ("Current market value, in EUR.", "Valore di mercato attuale, in EUR."),
    "adv.kpi_clients_sub": ("Saved client portfolios.", "Portafogli clienti salvati."),
    "adv.kpi_health_sub": ("Simple average across clients.", "Media semplice tra i clienti."),
    "adv.search": ("Search by client code", "Cerca per codice cliente"),
    "adv.col_client": ("Client", "Cliente"),
    "adv.col_profile": ("Profile", "Profilo"),
    "adv.col_value": ("Value", "Valore"),
    "adv.col_return": ("P&L since purchase", "P&L dal carico"),
    "adv.review_vol": (
        "Volatility {vol} above the {band} band of the {profile} profile.",
        "Volatilità {vol} oltre la banda del {band} del profilo {profile}.",
    ),
    "adv.review_health": (
        "Health Score {health} below the review threshold ({fair}).",
        "Health Score {health} sotto la soglia di revisione ({fair}).",
    ),
    "adv.col_vol": ("Volatility", "Volatilità"),
    "adv.col_health": ("Health", "Health"),
    "adv.col_flag": ("Main finding", "Segnalazione principale"),
    "adv.open": ("Open", "Apri"),
    "adv.no_clients_title": ("No clients yet", "Nessun cliente"),
    "adv.no_clients_hint": (
        "Create the first client with its positions, or start from a demo client "
        "to explore the analyses.",
        "Crea il primo cliente con le sue posizioni, oppure parti da un cliente "
        "dimostrativo per esplorare le analisi.",
    ),
    "adv.demo_client": ("Create demo client", "Crea cliente dimostrativo"),
    "adv.no_match": ("No client matches the search.", "Nessun cliente corrisponde alla ricerca."),
    "adv.analysis_failed": ("Analysis not available: {err}", "Analisi non disponibile: {err}"),
    "adv.new_title": ("New client", "Nuovo cliente"),
    "adv.new_sub": (
        "Enter a client code, the declared risk profile, the reference benchmark and the "
        "positions held. Prefer an internal code to the client's full name.",
        "Inserisci un codice cliente, il profilo di rischio dichiarato, il benchmark di "
        "riferimento e le posizioni detenute. Preferisci un codice interno al nome e "
        "cognome del cliente.",
    ),
    "adv.registry": ("Client details", "Anagrafica"),
    "adv.client_code": ("Client code", "Codice cliente"),
    "adv.client_code_help": (
        "An internal reference, e.g. C-0042. Avoiding names keeps personal data to a minimum.",
        "Un riferimento interno, es. C-0042. Evitare i nomi riduce al minimo i dati personali.",
    ),
    "adv.code_exists": (
        "A client with this code already exists.",
        "Esiste già un cliente con questo codice.",
    ),
    "adv.create": ("Create client", "Crea cliente"),
    "adv.create_disabled": (
        "Enter a client code and at least one position.",
        "Inserisci un codice cliente e almeno una posizione.",
    ),
    "adv.created": ("Client {name} created", "Cliente {name} creato"),
    "adv.meta": (
        "Risk profile: {profile} · Benchmark: {benchmark} · Positions: {n} · Updated {updated}",
        "Profilo di rischio: {profile} · Benchmark: {benchmark} · Posizioni: {n} · "
        "Aggiornato il {updated}",
    ),
    "adv.save": ("Save changes", "Salva modifiche"),
    "adv.saved": ("Changes saved", "Modifiche salvate"),
    "adv.unsaved": (
        "You have unsaved changes to this client's positions, risk profile or benchmark. "
        "They are kept while you move around the workspace, until you save or discard them.",
        "Hai modifiche non salvate alle posizioni, al profilo di rischio o al benchmark di "
        "questo cliente. Restano in sospeso mentre ti sposti nello spazio di lavoro, finché "
        "non le salvi o le annulli.",
    ),
    "adv.unsaved_short": ("unsaved changes", "modifiche non salvate"),
    "adv.pending_book": (
        "Unsaved changes for: {clients}. The table shows the saved values.",
        "Modifiche non salvate per: {clients}. La tabella mostra i valori salvati.",
    ),
    "adv.discard": ("Discard", "Annulla modifiche"),
    "adv.profile_note": (
        "The profile is saved together with the positions, with Save changes.",
        "Il profilo si salva insieme alle posizioni, con Salva modifiche.",
    ),
    "adv.benchmark": ("Reference benchmark", "Benchmark di riferimento"),
    "adv.benchmark_help": (
        "Market index for beta, alpha, correlation and the comparison charts, in the "
        "analysis and in the PDF reports. Choose the one that matches the client's "
        "investment universe: a portfolio of Italian stocks is measured against the "
        "FTSE MIB, not the Nasdaq-100.",
        "Indice di mercato per beta, alfa, correlazione e grafici di confronto, "
        "nell'analisi e nei report PDF. Scegli quello coerente con l'universo "
        "d'investimento del cliente: un portafoglio di titoli italiani si misura contro "
        "il FTSE MIB, non contro il Nasdaq-100.",
    ),
    "adv.benchmark_note": (
        "The benchmark is saved together with the positions, with Save changes.",
        "Il benchmark si salva insieme alle posizioni, con Salva modifiche.",
    ),
    "adv.recipient": ("Report heading (optional)", "Intestazione del report (facoltativa)"),
    "adv.recipient_placeholder": ("Client's full name", "Nome e cognome del cliente"),
    "adv.recipient_note": (
        "Printed only on the cover of the PDF you download now. It is kept in this "
        "browser session and never saved in the database.",
        "Stampata solo sul frontespizio del PDF che scarichi ora. Resta nella sessione "
        "del browser e non viene mai salvata nel database.",
    ),
    "adv.no_positions": (
        "This client has no positions yet: add them in Positions.",
        "Questo cliente non ha ancora posizioni: aggiungile nella sezione Posizioni.",
    ),
    "adv.danger_title": ("Delete client", "Elimina cliente"),
    "adv.market_sub": (
        "Nasdaq-100 overview, correlations and company financials.",
        "Panoramica Nasdaq-100, correlazioni e dati di bilancio delle società.",
    ),
    "adv.admin_sub": (
        "Platform counters and activity log. Never other advisors' portfolios.",
        "Contatori della piattaforma e registro delle attività. Mai i portafogli di altri consulenti.",
    ),
    "adv.empty_positions": (
        "Add instruments one by one or import the client's securities position from the broker.",
        "Aggiungi gli strumenti uno alla volta o importa la posizione titoli del cliente dal broker.",
    ),
    # ---------------------------------------------------------------- landing
    "landing.title": (
        "Your equity portfolio, measured on your own data",
        "Il tuo portafoglio azionario, misurato sui tuoi dati",
    ),
    "landing.sub": (
        "Risk, concentration, currency exposure and company quality, measured "
        "in euros on the positions you actually hold. No return forecasts: "
        "only what your data shows.",
        "Rischio, concentrazione, esposizione valutaria e qualità delle società, "
        "misurati in euro sulle posizioni effettivamente detenute. Nessuna "
        "previsione di rendimento: solo ciò che dicono i tuoi dati.",
    ),
    "landing.cta": ("Start the analysis", "Inizia l'analisi"),
    "landing.cta_note": (
        "No sign-up required · about one minute",
        "Nessuna registrazione richiesta · circa un minuto",
    ),
    "landing.panel": ("What the report includes", "Cosa contiene il report"),
    "landing.f1_t": ("Health Score", "Health Score"),
    "landing.f1_d": (
        "Six components: diversification, concentration, volatility, currency, "
        "drawdown and quality.",
        "Sei componenti: diversificazione, concentrazione, volatilità, valuta, "
        "drawdown e qualità.",
    ),
    "landing.f2_t": ("Risk in euros", "Rischio in euro"),
    "landing.f2_d": (
        "Volatility and drawdown computed in your currency, EUR/USD exchange risk included.",
        "Volatilità e drawdown calcolati nella tua valuta, rischio di cambio EUR/USD incluso.",
    ),
    "landing.f3_t": ("Risk contribution", "Contributo al rischio"),
    "landing.f3_d": (
        "How much of the total risk each position accounts for, beyond its weight.",
        "Quanto del rischio complessivo dipende da ciascuna posizione, oltre il suo peso.",
    ),
    "landing.f4_t": ("PDF report", "Report PDF"),
    "landing.f4_d": (
        "A four-page report to keep or share with your advisor.",
        "Un report di quattro pagine da conservare o condividere con il consulente.",
    ),
    "landing.fact1": (
        "Nasdaq-100 stocks with stored price history",
        "titoli Nasdaq-100 con storico prezzi",
    ),
    "landing.fact2": ("Health Score components", "componenti dell'Health Score"),
    "landing.fact3": (
        "base currency, exchange risk included",
        "valuta di riferimento, rischio di cambio incluso",
    ),
    "landing.legal": (
        "Informational tool. It does not constitute investment advice.",
        "Strumento informativo: non costituisce consulenza in materia di investimenti.",
    ),
    # ---------------------------------------------------------------- gate
    "gate.step1": ("Composition", "Composizione"),
    "gate.step2": ("Analysis", "Analisi"),
    "gate.title": ("Portfolio composition", "Composizione del portafoglio"),
    "gate.sub": (
        "Enter the positions you currently hold. The purchase price is taken "
        "from the adjusted close on the purchase date and can be edited.",
        "Inserisci le posizioni attualmente detenute. Il prezzo di carico è "
        "ricavato dalla chiusura rettificata alla data di acquisto ed è modificabile.",
    ),
    "gate.tab_manual": ("Manual entry", "Inserimento manuale"),
    "gate.tab_import": ("Import from file", "Importa da file"),
    "gate.tab_sample": ("Model portfolio", "Portafoglio dimostrativo"),
    "gate.instrument": ("Instrument", "Strumento"),
    "gate.search_placeholder": (
        "Ticker symbol, e.g. AAPL",
        "Simbolo, es. AAPL",
    ),
    "gate.add": ("Add", "Aggiungi"),
    "gate.add_position": ("Add", "Aggiungi"),
    "gate.your_holdings": ("Positions", "Posizioni"),
    "gate.col_instrument": ("Instrument", "Strumento"),
    "gate.col_avg_price": ("Avg. price", "Prezzo medio"),
    "gate.col_cost": ("Cost basis", "Controvalore"),
    "gate.col_weight": ("Weight", "Peso"),
    "gate.clear": ("Clear all", "Svuota elenco"),
    "gate.empty_title": ("No positions entered", "Nessuna posizione inserita"),
    "gate.empty_hint": (
        "Add instruments one by one, import your broker's securities position, "
        "or load the model portfolio.",
        "Aggiungi gli strumenti uno alla volta, importa la posizione titoli del "
        "tuo broker oppure carica il portafoglio dimostrativo.",
    ),
    "gate.import_desc": (
        "Upload the securities position exported from your broker (CSV or "
        "Excel). Required columns: ticker/symbol and amount/value, or quantity "
        "and price. The file replaces the positions entered so far.",
        "Carica la posizione titoli esportata dal tuo broker (CSV o Excel). "
        "Colonne richieste: ticker/simbolo e importo/controvalore, oppure "
        "quantità e prezzo. Il file sostituisce le posizioni inserite finora.",
    ),
    "gate.sample_desc": (
        "Three US large-cap positions (Apple, Microsoft, NVIDIA) with "
        "purchase lots between 2024 and 2025. Useful to review the analysis "
        "before entering your own data.",
        "Tre posizioni large-cap USA (Apple, Microsoft, NVIDIA) con lotti di "
        "acquisto tra il 2024 e il 2025. Utile per esaminare l'analisi prima di "
        "inserire i propri dati.",
    ),
    "gate.sample": ("Load model portfolio", "Carica portafoglio dimostrativo"),
    "gate.summary": ("Summary", "Riepilogo"),
    "gate.sum_positions": ("Positions", "Posizioni"),
    "gate.sum_invested": ("Invested (cost basis)", "Investito (carico)"),
    "gate.sum_largest": ("Largest position", "Posizione principale"),
    "gate.sum_top3": ("Top 3 weight", "Peso prime 3"),
    "gate.analyze": ("Run analysis", "Avvia l'analisi"),
    "gate.analyze_disabled": (
        "Add at least one position to run the analysis.",
        "Aggiungi almeno una posizione per avviare l'analisi.",
    ),
    "gate.analyze_note": (
        "Daily adjusted closes · values in EUR with currency risk · not investment advice.",
        "Chiusure giornaliere rettificate · valori in EUR con rischio cambio · "
        "non costituisce consulenza finanziaria.",
    ),
    "gate.loading_title": ("Preparing the analysis", "Preparazione dell'analisi"),
    "gate.loading_sub": ("{n} positions", "{n} posizioni"),
    "gate.load_prices": ("Historical prices", "Prezzi storici"),
    "gate.load_fx": ("EUR/USD exchange rate", "Cambio EUR/USD"),
    "gate.load_fundamentals": ("Company financials", "Dati di bilancio"),
    "gate.load_rates": ("Risk-free rate", "Tasso privo di rischio"),
    # ---------------------------------------------------------------- sidebar
    "side.logout": ("Log out", "Esci"),
    "side.my_portfolio": ("My portfolio", "Il mio portafoglio"),
    "period.1mo": ("1 month", "1 mese"),
    "period.6mo": ("6 months", "6 mesi"),
    "period.1y": ("1 year", "1 anno"),
    "period.2y": ("2 years", "2 anni"),
    "period.5y": ("5 years", "5 anni"),
    "side.add_stock": ("Add a stock", "Aggiungi un titolo"),
    "side.search_hint": (
        "Search a stock to see its name and price, then add it.",
        "Cerca un titolo per vederne nome e prezzo, poi aggiungilo.",
    ),
    "side.your_holdings": (
        "Your holdings · weights at cost",
        "Le tue posizioni · pesi sul carico",
    ),
    "side.amount": ("Amount (€)", "Importo (€)"),
    "side.save": ("Save", "Salva"),
    "side.remove": ("Remove", "Rimuovi"),
    "side.edit": ("Edit", "Modifica"),
    "side.delete_confirm": (
        'Permanently delete "{name}" and its analysis history',
        'Elimina definitivamente "{name}" e il suo storico analisi',
    ),
    "side.delete_btn": ("Delete client portfolio", "Elimina portafoglio cliente"),
    "side.deleted_toast": ("Client portfolio deleted", "Portafoglio cliente eliminato"),
    "side.privacy": ("Privacy and data", "Privacy e dati"),
    "side.erase_all_hint": (
        "Deletes all your saved portfolios and analyses. Security log entries are kept, with your email replaced by a random code not derived from it and their details removed. The action cannot be undone.",
        "Elimina tutti i portafogli e le analisi salvate. Le voci del registro di sicurezza restano, con l'email sostituita da un codice casuale non derivato da essa e senza dettagli. L'operazione non è reversibile.",
    ),
    "side.erase_all_confirm": (
        "I understand that all my data will be deleted",
        "Ho capito che tutti i miei dati verranno eliminati",
    ),
    "side.erase_all_btn": ("Delete all my data", "Elimina tutti i miei dati"),
    "side.erase_all_done": (
        "Deleted {portfolios} portfolios and {analyses} analyses; {audit_pseudonymized} log entries de-identified.",
        "Eliminati {portfolios} portafogli e {analyses} analisi; {audit_pseudonymized} voci di registro rese non riconducibili.",
    ),
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
        "Supported formats: CSV and Excel; PDFs are not readable. "
        "Expected columns: ticker/symbol and amount/value, or quantity and price.",
        "Esporta la POSIZIONE TITOLI del tuo broker (detta anche dossier o "
        "portafoglio), non l'estratto conto movimenti. Formati supportati: "
        "CSV ed Excel; i PDF non sono leggibili. Colonne attese: "
        "ticker/simbolo e importo/controvalore, oppure quantità e prezzo.",
    ),
    "side.imported": ("Imported {n} positions", "Importate {n} posizioni"),
    "side.import_failed": ("Import failed: {err}", "Import non riuscito: {err}"),
    "side.settings": ("Settings", "Impostazioni"),
    "side.language": ("Language / Lingua", "Lingua / Language"),
    "side.horizon": ("Historical horizon", "Orizzonte storico"),
    "side.in_eur": ("Measure everything in euros", "Misura tutto in euro"),
    "side.in_eur_help": (
        "US stocks trade in dollars: converting to EUR makes the metrics "
        "include EUR/USD swings too: the real risk for a European investor.",
        "I titoli USA quotano in dollari: convertire in EUR fa includere alle "
        "metriche anche le oscillazioni EUR/USD, il rischio reale per un "
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
        "Health Score: the average of six components: diversification, "
        "concentration, volatility, currency exposure, drawdown, "
        "balance-sheet quality.",
        "Health Score: la media di sei componenti: diversificazione, "
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
    "chk.col_weight": ("Weight", "Peso"),
    "chk.col_return": ("Return ({period})", "Rendimento ({period})"),
    "chk.col_trend": ("Trend ({period})", "Andamento ({period})"),
    "chk.top_problems": ("Top problems", "Problemi principali"),
    "chk.profile_problem": (
        "Annualized volatility exceeds the {band} band of the declared **{profile}** profile by **{excess}**.",
        "La volatilità annualizzata supera del **{excess}** la banda del {band} del profilo dichiarato **{profile}**.",
    ),
    "chk.no_problems": (
        "No problems flagged by the monitored rules.",
        "Nessun problema segnalato dalle regole monitorate.",
    ),
    "chk.risk_eur": ("Your risk, in euros", "Il tuo rischio, in euro"),
    "chk.kpi_swing": ("Typical 1-year swing", "Oscillazione tipica a 1 anno"),
    "chk.kpi_swing_sub": ("{vol} per year · ", "{vol} all'anno · "),
    "chk.kpi_var": ("Daily VaR 95%", "VaR giornaliero 95%"),
    "chk.kpi_var_sub": (
        "loss not exceeded on 95% of observed days (historical estimate)",
        "perdita non superata nel 95% dei giorni osservati (stima storica)",
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
        "Scenario: {ticker} at half its current weight, redistributed pro rata",
        "Scenario: {ticker} a metà del peso attuale, ridistribuito in proporzione",
    ),
    "chk.equalize": (
        "Scenario: equal weights across current holdings",
        "Scenario: pesi uguali sui titoli attuali",
    ),
    "chk.sim_text": (
        "**{name}**: annualized volatility in EUR from ± {vol_from} to ± {vol_to}; Health Score from {h_from} to **{h_to}**.",
        "**{name}**: volatilità annualizzata in euro da ± {vol_from} a ± {vol_to}; Health Score da {h_from} a **{h_to}**.",
    ),
    "chk.no_improve": (
        "The standard rebalancing simulations on the current holdings (halving the "
        "largest position, equal weights) **do not improve the current profile**:",
        "Le simulazioni di ribilanciamento standard sui titoli attuali (dimezzare la "
        "prima posizione, pesi uguali) **non migliorano il profilo attuale**:",
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
    "m.maxdd": ("Max drawdown", "Max drawdown"),
    "cov.note": (
        "{ticker} priced only from {date}: its metrics use the shorter overlap",
        "{ticker} quotato solo dal {date}: le sue metriche usano la sovrapposizione più corta",
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
    "pdf.prepared_by": ("prepared by {advisor}", "predisposto da {advisor}"),
    "pdf.prepared_for": ("Prepared for {recipient}", "Preparato per {recipient}"),
    "pdf.profile": ("{profile} profile", "profilo {profile}"),
    "pdf.window": (
        "observation window {start} – {end}",
        "finestra di osservazione {start} – {end}",
    ),
    "pdf.generated": ("generated on {now}", "generato il {now}"),
    "pdf.no_summary": (
        "Summary not available for this analysis.",
        "Sintesi non disponibile per questa analisi.",
    ),
    "pdf.within": ("within", "entro"),
    "pdf.outside": ("OUTSIDE", "FUORI DA"),
    "pdf.check_caveat": (
        "Volatility-only software check: it does not replace the MiFID II "
        "suitability assessment, which remains the responsibility of the advisor.",
        "Verifica software sulla sola volatilità: non sostituisce la "
        "valutazione di adeguatezza MiFID II, che resta responsabilità del consulente.",
    ),
    "pdf.no_history": ("Price history not available.", "Storico prezzi non disponibile."),
    "pdf.h_ticker": ("Ticker", "Ticker"),
    "pdf.h_company": ("Company", "Società"),
    "pdf.h_return": ("Return {period}", "Rend. {period}"),
    "pdf.other_holdings": ("other holdings", "altre posizioni"),
    "pdf.coverage": ("Data coverage: ", "Copertura dati: "),
    "pdf.portfolio_legend": ("Portfolio", "Portafoglio"),
    "pdf.trough": ("trough {dd} on {date}", "minimo {dd} il {date}"),
    "pdf.h_metric": ("Metric", "Metrica"),
    "pdf.h_portfolio": ("Portfolio", "Portafoglio"),
    "pdf.underwater_title": (
        "Distance from the peak (underwater)",
        "Distanza dal massimo (underwater)",
    ),
    "pdf.monthly_title": (
        "Monthly returns (last 12 months)",
        "Rendimenti mensili (ultimi 12 mesi)",
    ),
    "pdf.wr_title": ("Weight vs risk contribution", "Peso vs contributo al rischio"),
    "pdf.legend_weight": ("capital weight", "peso sul capitale"),
    "pdf.legend_risk": ("share of portfolio risk", "quota del rischio di portafoglio"),
    "pdf.sector_title": ("Allocation by sector", "Allocazione per settore"),
    "pdf.other_sectors": ("Other sectors", "Altri settori"),
    "pdf.not_classified": ("Not classified", "Non classificato"),
    "pdf.c_holdings": ("HOLDINGS", "POSIZIONI"),
    "pdf.c_effective": ("EFFECTIVE HOLDINGS", "POSIZIONI EFFETTIVE"),
    "pdf.c_hhi": ("CONCENTRATION (HHI)", "CONCENTRAZIONE (HHI)"),
    "pdf.no_scenario": (
        "No stress scenario computed for this portfolio.",
        "Nessuno scenario di stress calcolato per questo portafoglio.",
    ),
    "pdf.attention_title": ("Points of attention", "Punti di attenzione"),
    "pdf.none_flagged": (
        "Nothing flagged by the monitored rules.",
        "Nulla da segnalare secondo le regole monitorate.",
    ),
    "pdf.notices_title": (
        "Methodology, assumptions & important notices",
        "Metodologia, assunzioni e avvertenze importanti",
    ),
    "pdf.notice_caution": (
        "CAUTION: the observation window is shorter than one year, so annualized figures (CAGR, volatility, Sharpe/Sortino) extrapolate from few months "
        "and should be read as indicative only.",
        "ATTENZIONE: la finestra di osservazione è inferiore a un anno: i valori annualizzati (CAGR, volatilità, Sharpe/Sortino) estrapolano da "
        "pochi mesi e vanno letti come puramente indicativi.",
    ),
    "pdf.notice_costs": (
        "All figures are gross of transaction costs, management fees and "
        "taxes, which would reduce the results shown.",
        "Tutti i valori sono al lordo di costi di transazione, commissioni di "
        "gestione e imposte, che ridurrebbero i risultati mostrati.",
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
    "pdf.footer_line2": (
        "Return figures apply current weights to past prices (simulated past performance). Past performance is not a reliable indicator of future results. Not investment advice, research, an offer or a solicitation.",
        "I rendimenti applicano i pesi attuali ai prezzi passati (performance passata simulata). I rendimenti passati non sono un indicatore affidabile dei risultati futuri. Non è consulenza, ricerca, offerta né sollecitazione.",
    ),
    # ---------------------------------------------------------------- positions / P&L
    "pos.qty": ("Quantity", "Quantità"),
    "pos.buy_price": ("Purchase price", "Prezzo di carico"),
    "pos.current_price": ("Current price", "Prezzo attuale"),
    "pos.value": ("Value", "Valore"),
    "pos.pnl": ("P&L", "P&L"),
    "pos.total_cost": (
        "Invested (cost basis): **{total}** · {n} stocks",
        "Investito (carico): **{total}** · {n} titoli",
    ),
    "pos.cost_unknown": (
        "Purchase price not available for some positions (saved or imported "
        "without cost data): their P&L is not shown. Edit the position to add it.",
        "Prezzo di carico non disponibile per alcune posizioni (salvate o "
        "importate senza dato di costo): il loro P&L non viene mostrato. "
        "Modifica la posizione per inserirlo.",
    ),
    "hero.gain_line": (
        "P&L {amount} ({pct}) since purchase",
        "P&L {amount} ({pct}) dal carico",
    ),
    "pdf.h_pnl": ("P&L", "P&L"),
    "pdf.notice_pnl": (
        "P&L per position = quantity × (current price − average purchase "
        "price), both converted at today's exchange rate: it isolates the "
        "price move of the instrument. Dividends received and transaction "
        "costs are not included. Positions without purchase-price data show "
        "no P&L.",
        "P&L per posizione = quantità × (prezzo attuale − prezzo medio di "
        "carico), entrambi convertiti al cambio odierno: isola il movimento "
        "di prezzo dello strumento. Dividendi incassati e costi di "
        "transazione non sono inclusi. Le posizioni senza prezzo di carico "
        "non mostrano P&L.",
    ),
    # ---------------------------------------------------------------- date & IRR
    "pos.buy_date": ("Purchase date", "Data di acquisto"),
    "pos.price_auto_help": (
        "Auto-filled with the adjusted close of the purchase date (price database). Override it if you know your exact fill. Current price: "
        "{current}.",
        "Compilato da solo con la chiusura rettificata della data di acquisto "
        "(database prezzi). Correggilo se conosci il tuo eseguito esatto. "
        "Prezzo attuale: {current}.",
    ),
    "pos.price_lookup_failed": (
        "No historical price found for {ticker} on {date}: enter the purchase price manually.",
        "Nessun prezzo storico trovato per {ticker} al {date}: inserisci il "
        "prezzo di carico a mano.",
    ),
    "pos.days": ("Days held", "Giorni"),
    "pos.ann": ("IRR / yr", "IRR annuo"),
    "hero.irr": (" · IRR {irr}/yr", " · IRR {irr}/anno"),
    # ---------------------------------------------------------------- options overlay
    "nav.options": ("Options", "Opzioni"),
    "opt.title": (
        "Options overlay: protection and income scenarios",
        "Overlay di opzioni: scenari di protezione e rendita",
    ),
    "opt.intro": (
        "Theoretical scenarios on a position already held: a protective put or a "
        "collar sets a floor on the exit price; a covered call collects a premium "
        "in exchange for upside above the strike. Figures are Black-Scholes "
        "estimates on realized volatility. No strategy guarantees a profit.",
        "Scenari teorici su una posizione già detenuta: una put protettiva o un "
        "collar fissano un pavimento al prezzo di uscita; una covered call incassa "
        "un premio in cambio del rialzo oltre lo strike. Le cifre sono stime "
        "Black-Scholes sulla volatilità realizzata. Nessuna strategia garantisce "
        "un profitto.",
    ),
    "opt.pick": ("Position", "Posizione"),
    "opt.horizon": ("Horizon", "Orizzonte"),
    "opt.put_strike": ("Put strike (% of price)", "Strike put (% del prezzo)"),
    "opt.put_strike_abs": ("Put strike", "Strike put"),
    "opt.call_strike": ("Call strike (% of price)", "Strike call (% del prezzo)"),
    "opt.vol_used": (
        "Inputs: realized annual volatility {vol} over the selected period, "
        "risk-free rate {rf}, current price {spot}.",
        "Input: volatilità annua realizzata {vol} nel periodo selezionato, "
        "tasso privo di rischio {rf}, prezzo attuale {spot}.",
    ),
    "opt.protect_title": ("Protective put", "Put protettiva"),
    "opt.protect_text": (
        "A put with strike {strike} and {days} days to expiry is estimated at "
        "≈ **{premium}** per share ({pct} of the position value). Until expiry it "
        "gives the right to sell at {strike}: net of the premium, the minimum "
        "exit price is **{floor}** per share.",
        "Una put con strike {strike} e {days} giorni alla scadenza è stimata "
        "≈ **{premium}** per azione ({pct} del valore della posizione). Fino alla "
        "scadenza dà il diritto di vendere a {strike}: al netto del premio, il "
        "prezzo minimo di uscita è **{floor}** per azione.",
    ),
    "opt.locked_gain": (
        "Against an average cost of {cost}, the minimum P&L at expiry is "
        "**{pnl}** per share (**{total}** on the whole position).",
        "Rispetto al prezzo medio di carico di {cost}, il P&L minimo alla "
        "scadenza è **{pnl}** per azione (**{total}** sull'intera posizione).",
    ),
    "opt.locked_loss": (
        "Against an average cost of {cost}, the floor sits at {pnl} per share: "
        "the put limits the loss, it does not create a gain.",
        "Rispetto al prezzo medio di carico di {cost}, il pavimento è a {pnl} per "
        "azione: la put limita la perdita, non crea un guadagno.",
    ),
    "opt.income_title": ("Covered call", "Covered call"),
    "opt.income_text": (
        "A call sold at {strike} with {days} days to expiry is estimated at "
        "≈ **{premium}** per share: **{yld}** of the position over the period. "
        "Above {strike} the shares are called away and further upside is forgone.",
        "Una call venduta a {strike} con {days} giorni alla scadenza è stimata "
        "≈ **{premium}** per azione: **{yld}** della posizione nel periodo. Sopra "
        "{strike} le azioni vengono ritirate e il rialzo ulteriore non è incassato.",
    ),
    "opt.income_annual": (
        "(about {ann} annualized; {total} on the whole position)",
        "(circa {ann} annualizzato; {total} sull'intera posizione)",
    ),
    "opt.collar_title": ("Zero-cost collar", "Collar a costo zero"),
    "opt.collar_text": (
        "A call sold at **{cap}** finances the put at {floor} almost exactly "
        "(net premium ≈ {net}): a price corridor from {floor} to {cap} at about "
        "zero cost. Floor and cap both apply until expiry.",
        "Una call venduta a **{cap}** finanzia quasi esattamente la put a {floor} "
        "(premio netto ≈ {net}): un corridoio di prezzo da {floor} a {cap} a costo "
        "circa zero. Pavimento e tetto valgono entrambi fino alla scadenza.",
    ),
    "opt.disclaimer": (
        "Theoretical Black-Scholes estimates on realized volatility: no "
        "implied-volatility surface, dividends ignored, European exercise. "
        "Actual market prices and availability differ. Listed options cover "
        "100 shares per contract, so sizes may not match the position. Options "
        "are complex instruments subject to the MiFID II appropriateness "
        "assessment; this panel is a scenario tool, not investment advice or a "
        "recommendation. No strategy guarantees a profit.",
        "Stime teoriche Black-Scholes sulla volatilità realizzata: nessuna "
        "superficie di volatilità implicita, dividendi ignorati, esercizio "
        "europeo. Prezzi e disponibilità reali di mercato differiscono. Le "
        "opzioni quotate coprono 100 azioni per contratto: le taglie possono non "
        "combaciare con la posizione. Le opzioni sono strumenti complessi soggetti "
        "alla valutazione di appropriatezza MiFID II; questo pannello è uno "
        "strumento di scenario, non consulenza né raccomandazione. Nessuna "
        "strategia garantisce un profitto.",
    ),
    "opt.no_positions": (
        "This panel needs at least one position with quantity and purchase price. "
        "They can be entered in the client's portfolio composition.",
        "Questo pannello richiede almeno una posizione con quantità e prezzo di "
        "carico, inseribili nella composizione del portafoglio del cliente.",
    ),
    "opt.days_label": ("{days} days", "{days} giorni"),
    "opt.market_title": ("Market check: real quotes", "Verifica di mercato: quotazioni reali"),
    "opt.mkt_estimate": ("Estimate (BS)", "Stima (BS)"),
    "opt.mkt_market": ("Market (mid)", "Mercato (mid)"),
    "opt.mkt_iv": ("Implied volatility", "Volatilità implicita"),
    "opt.mkt_details": (
        "Real contract: strike {strike}, expiry {expiry} ({days} days) · bid "
        "{bid} / ask {ask} · last trade {last} · open interest {oi}. The "
        "theoretical estimate above is recomputed at the SAME strike and "
        "expiry, so the comparison is apples to apples.",
        "Contratto reale: strike {strike}, scadenza {expiry} ({days} giorni) · "
        "denaro {bid} / lettera {ask} · ultimo scambio {last} · open interest "
        "{oi}. La stima teorica qui sopra è ricalcolata sugli stessi strike e "
        "scadenza: le due cifre sono direttamente confrontabili.",
    ),
    "opt.iv_note": (
        "The market prices {iv} implied volatility vs {rv} realized over the "
        "selected period: {verdict}",
        "Il mercato prezza una volatilità implicita del {iv} contro il {rv} "
        "realizzato nel periodo selezionato: {verdict}",
    ),
    "opt.iv_higher": (
        "options are trading rich versus recent history.",
        "le opzioni quotano care rispetto alla storia recente.",
    ),
    "opt.iv_lower": (
        "options are trading cheap versus recent history.",
        "le opzioni quotano a sconto rispetto alla storia recente.",
    ),
    "opt.iv_inline": (
        "the market broadly agrees with recent history.",
        "il mercato è sostanzialmente allineato alla storia recente.",
    ),
    "opt.compare_put_title": (
        "Listed put contracts near the selected level",
        "Contratti put quotati vicino al livello scelto",
    ),
    "opt.compare_call_title": (
        "Listed call contracts near the selected level",
        "Contratti call quotati vicino al livello scelto",
    ),
    "opt.compare_caption": (
        "Market data, not advice: listed contracts near the selected levels, side "
        "by side. The platform does not select instruments.",
        "Dati di mercato, non consigli: i contratti quotati vicino ai livelli "
        "scelti, fianco a fianco. La piattaforma non seleziona strumenti.",
    ),
    "opt.col_strike": ("Strike", "Strike"),
    "opt.col_strike_pct": ("% of price", "% del prezzo"),
    "opt.col_mid": ("Mid", "Mid"),
    "opt.col_cost_pct": ("Cost %", "Costo %"),
    "opt.col_cost_month": ("Cost %/month", "Costo %/mese"),
    "opt.col_floor": ("Floor", "Pavimento"),
    "opt.col_locked": ("Locked P&L", "P&L bloccato"),
    "opt.col_yield": ("Yield (period)", "Rendita (periodo)"),
    "opt.col_yield_ann": ("Yield (annualized)", "Rendita (annualizzata)"),
    "opt.col_income": ("Income", "Incasso"),
    "opt.col_iv": ("IV", "IV"),
    "opt.col_oi": ("Open int.", "Open int."),
    "opt.market_unavailable": (
        "Live option quotes not available right now (Yahoo options endpoint): "
        "showing theoretical estimates only.",
        "Quotazioni opzioni non disponibili in questo momento (endpoint "
        "opzioni di Yahoo): solo stime teoriche.",
    ),
    # ---------------------------------------------------------------- components
    "hero.value": ("Portfolio value", "Valore del portafoglio"),
    "hero.last_session": ("Last session", "Ultima seduta"),
    "hero.score_built": ("HOW THE SCORE IS BUILT", "COME NASCE IL PUNTEGGIO"),
    "hero.dna_title": ("PORTFOLIO DNA", "DNA DEL PORTAFOGLIO"),
    # ---------------------------------------------------------------- analisi (metriche)
    "an.return": ("Return", "Rendimento"),
    "an.risk": ("Risk", "Rischio"),
    "an.market_value": ("Market value", "Valore di mercato"),
    "an.cagr": ("Annualized return (CAGR)", "Rendimento annualizzato (CAGR)"),
    "an.cagr_help": (
        "Compound annual growth rate over the observed period.",
        "Tasso di crescita annuo composto sul periodo osservato.",
    ),
    "an.sharpe": ("Sharpe ratio", "Indice di Sharpe"),
    "an.sharpe_help": ("Risk-free rate used: {rf}.", "Tasso privo di rischio usato: {rf}."),
    "an.sortino": ("Sortino ratio", "Indice di Sortino"),
    "an.vol": ("Volatility (annualized)", "Volatilità (annualizzata)"),
    "an.maxdd": ("Maximum drawdown", "Massimo drawdown"),
    "an.var": ("VaR 95% (1 day)", "VaR 95% (1 giorno)"),
    "an.var_caption": (
        "Historical: on 95% of the observed days the loss did not exceed this amount.",
        "Storico: nel 95% dei giorni osservati la perdita non ha superato questo importo.",
    ),
    "an.beta": ("Beta vs {benchmark}", "Beta vs {benchmark}"),
    "an.alpha_delta": ("Alpha {alpha} p.a.", "Alfa {alpha} annuo"),
    "an.estimates": (
        "Estimates from historical data: not a forecast.",
        "Stime su dati storici: non sono previsioni.",
    ),
    "an.vs_bench": (
        "Portfolio vs {benchmark}, rebased to 100",
        "Portafoglio vs {benchmark}, base 100",
    ),
    "an.excess": (
        "Excess return over the period versus the benchmark: **{excess}**",
        "Extra-rendimento sul periodo rispetto al benchmark: **{excess}**",
    ),
    "an.excess_fx": (
        " (including the EUR/USD effect).",
        " (incluso l'effetto del cambio EUR/USD).",
    ),
    "an.underwater": ("Drawdown from the previous peak", "Drawdown dal massimo precedente"),
    "an.underwater_caption": (
        "Distance from the running peak: every value below zero is time spent under water.",
        "Distanza dal massimo raggiunto: ogni valore sotto zero è tempo passato sotto il picco.",
    ),
    "an.distribution": (
        "Distribution of daily returns",
        "Distribuzione dei rendimenti giornalieri",
    ),
    "an.distribution_caption": (
        "Each bar counts the days with that return. The red line marks the historical "
        "95% VaR: only 5% of days were worse.",
        "Ogni barra conta i giorni con quel rendimento. La linea rossa segna il VaR storico "
        "al 95%: solo il 5% dei giorni è andato peggio.",
    ),
    "an.rolling_vol": (
        "Annualized volatility, 60-day rolling",
        "Volatilità annualizzata, finestra mobile 60 giorni",
    ),
    "an.rolling_vol_caption": (
        "How the portfolio's risk level changed over time.",
        "Come è cambiato nel tempo il livello di rischio del portafoglio.",
    ),
    "an.rolling_beta": (
        "Beta vs {benchmark}, 60-day rolling",
        "Beta vs {benchmark}, finestra mobile 60 giorni",
    ),
    "an.rolling_beta_caption": (
        "Above 1 the portfolio amplifies benchmark moves, below 1 it dampens them.",
        "Sopra 1 il portafoglio amplifica i movimenti del benchmark, sotto 1 li attenua.",
    ),
    "an.attribution": (
        "Return attribution by position (EUR)",
        "Attribuzione del risultato per posizione (EUR)",
    ),
    "an.attribution_caption": (
        "Current amount × security return over the period (constant weights): "
        "the sum approximates the total result.",
        "Importo attuale × rendimento del titolo sul periodo (pesi costanti): "
        "la somma approssima il risultato totale.",
    ),
    "an.allocation": ("Allocation", "Allocazione"),
    "an.base100": ("Securities rebased to 100", "Titoli in base 100"),
    # ---------------------------------------------------------------- grafici
    "vis.auto": ("Rule-based commentary", "Commento basato su regole"),
    "vis.auto_caption": (
        "Generated by deterministic rules on the computed metrics, not by a language model.",
        "Generato da regole deterministiche sulle metriche calcolate, non da un modello linguistico.",
    ),
    "vis.radar": ("Risk profile by dimension", "Profilo di rischio per dimensione"),
    "vis.galaxy": ("Correlation map", "Mappa delle correlazioni"),
    "vis.galaxy_caption": (
        "Size = weight · color = return · distance = correlation",
        "Dimensione = peso · colore = rendimento · distanza = correlazione",
    ),
    "vis.need_two": ("At least two securities are needed.", "Servono almeno due titoli."),
    "vis.monthly": ("Monthly returns", "Rendimenti mensili"),
    "vis.best_worst": (
        "Best month: **{best}** ({best_ret}) · worst: **{worst}** ({worst_ret})",
        "Mese migliore: **{best}** ({best_ret}) · peggiore: **{worst}** ({worst_ret})",
    ),
    "vis.too_short": (
        "Period too short for the monthly view.",
        "Periodo troppo breve per la vista mensile.",
    ),
    "vis.weight_risk": (
        "Capital weight vs risk contribution",
        "Peso sul capitale vs contributo al rischio",
    ),
    "vis.how_to_read": ("Reading", "Lettura"),
    "vis.weight_risk_text": (
        "When the amber bar exceeds the blue one, the security weighs on risk more than "
        "on capital. **{ticker}** accounts for **{share}** of total risk ({gap} versus its weight).",
        "Quando la barra ambra supera quella blu, il titolo pesa sul rischio più che sul "
        "capitale. **{ticker}** spiega il **{share}** del rischio totale ({gap} rispetto al peso).",
    ),
    "vis.mcr_caption": (
        "Marginal contribution to portfolio variance: it accounts for volatilities and "
        "correlations, not only for the amount invested.",
        "Contributo marginale alla varianza del portafoglio: considera volatilità e "
        "correlazioni, non solo l'importo investito.",
    ),
    "vis.shock": ("Single-security shock", "Shock su un singolo titolo"),
    "vis.shock_ticker": ("Security", "Titolo"),
    "vis.shock_size": ("Price change", "Variazione di prezzo"),
    "vis.shock_today": ("Current value", "Valore attuale"),
    "vis.shock_total": ("After the shock (with contagion)", "Dopo lo shock (con contagio)"),
    "vis.shock_direct": ("Direct effect only", "Solo effetto diretto"),
    "vis.shock_caption": (
        "Contagion estimates how the other holdings would react, using their historical "
        "betas to the shocked security.",
        "Il contagio stima la reazione degli altri titoli tramite i loro beta storici "
        "verso il titolo colpito.",
    ),
    # ---------------------------------------------------------------- ottimizzazione
    "mvo.need_two": (
        "At least two securities are needed for the optimization.",
        "Servono almeno due titoli per l'ottimizzazione.",
    ),
    "mvo.title": ("Markowitz efficient frontier", "Frontiera efficiente di Markowitz"),
    "mvo.caption": (
        "For each risk level, the highest return achievable by combining the current "
        "holdings (expected returns = historical arithmetic means, Markowitz convention).",
        "Per ogni livello di rischio, il rendimento più alto ottenibile combinando i titoli "
        "in portafoglio (rendimenti attesi = medie aritmetiche storiche, convenzione di Markowitz).",
    ),
    "mvo.current": ("Current", "Attuale"),
    "mvo.min_var": ("Minimum variance", "Minima varianza"),
    "mvo.max_sharpe": ("Maximum Sharpe", "Massimo Sharpe"),
    "mvo.comparison": ("Comparison", "Confronto"),
    "mvo.portfolio": ("Portfolio", "Portafoglio"),
    "mvo.exp_return": ("Expected return (ann.)", "Rendimento atteso (ann.)"),
    "mvo.volatility": ("Volatility (ann.)", "Volatilità (ann.)"),
    "mvo.weights": ("Model weights", "Pesi dei modelli"),
    "mvo.weights_caption": (
        "Output of the historical optimization, for analysis only: not a recommendation "
        "to buy or sell.",
        "Risultato dell'ottimizzazione storica, solo a fini di analisi: non è una "
        "raccomandazione di acquisto o vendita.",
    ),
    # ---------------------------------------------------------------- fondamentali
    "fund.title": (
        "Revenue, margins, debt, growth and multiples",
        "Ricavi, margini, debito, crescita e multipli",
    ),
    "fund.tickers": ("Tickers separated by spaces", "Ticker separati da spazi"),
    "fund.name": ("Name", "Nome"),
    "fund.sector": ("Sector", "Settore"),
    "fund.div_yield": ("Div. yield", "Rend. dividendo"),
    "fund.revenue": ("Revenue (TTM)", "Ricavi (12 mesi)"),
    "fund.net_income": ("Net income (TTM)", "Utile netto (12 mesi)"),
    "fund.gross_margin": ("Gross margin", "Margine lordo"),
    "fund.op_margin": ("Operating margin", "Margine operativo"),
    "fund.net_margin": ("Net margin", "Margine netto"),
    "fund.debt": ("Debt", "Debito"),
    "fund.de": ("Debt/Equity", "Debito/Patrimonio"),
    "fund.rev_growth": ("Revenue growth", "Crescita ricavi"),
    "fund.eps_growth": ("Earnings growth", "Crescita utili"),
    "fund.fwd_pe": ("Forward P/E", "P/E prospettico"),
    "fund.source": ("Source", "Fonte"),
    "fund.caption": (
        "SEC EDGAR rows: last 12 months from the filed 10-K/10-Q; debt excludes leases; "
        "sector derived from the SIC code; no forward P/E (it requires analyst estimates). "
        "Other rows come from the backup sources.",
        "Righe SEC EDGAR: ultimi 12 mesi dai 10-K/10-Q depositati; il debito esclude i "
        "leasing; settore ricavato dal codice SIC; nessun P/E prospettico (richiede stime "
        "degli analisti). Le altre righe vengono dalle fonti di riserva.",
    ),
    "fund.card": ("Security profile", "Scheda titolo"),
    "fund.stock": ("Security", "Titolo"),
    "fund.dna_title": ("SECURITY PROFILE", "PROFILO DEL TITOLO"),
    "fund.overall": ("Composite score", "Punteggio composito"),
    "fund.overall_help": (
        "Weighted average: growth 35%, quality 35%, valuation 20%, low risk 10%. "
        "A heuristic, not investment advice.",
        "Media ponderata: crescita 35%, qualità 35%, valutazione 20%, basso rischio 10%. "
        "Un'euristica, non una consulenza.",
    ),
    "fund.card_vol": ("Annualized volatility: {vol}", "Volatilità annualizzata: {vol}"),
    # ---------------------------------------------------------------- mercato
    "mkt.title": ("Nasdaq-100 constituents compared", "I costituenti del Nasdaq-100 a confronto"),
    "mkt.period": ("Period", "Periodo"),
    "mkt.p_30": ("1 month", "1 mese"),
    "mkt.p_182": ("6 months", "6 mesi"),
    "mkt.p_365": ("1 year", "1 anno"),
    "mkt.p_730": ("2 years", "2 anni"),
    "mkt.p_1826": ("5 years", "5 anni"),
    "mkt.scatter": (
        "**Risk vs return ({period})**: one dot per security",
        "**Rischio vs rendimento ({period})**: un punto per titolo",
    ),
    "mkt.vol": ("Volatility (ann.)", "Volatilità (ann.)"),
    "mkt.ret": ("Return ({period})", "Rendimento ({period})"),
    "mkt.ranking": ("Full ranking", "Classifica completa"),
    "mkt.caption": (
        "Cumulative return over the period, USD prices.",
        "Rendimento cumulato sul periodo, prezzi in USD.",
    ),
    "mkt.pi_title": ("Multifactor ranking (PI Score)", "Classifica multifattoriale (PI Score)"),
    "mkt.pi_caption": (
        "Composite score 0-100: **50% 12-1 month momentum** (Jegadeesh & Titman 1993), "
        "**30% low volatility** (Baker et al. 2011), **20% trend** (distance from the "
        "200-day average). Regularities documented in the literature, not guarantees, "
        "and not investment advice.",
        "Punteggio composito 0-100: **50% momentum 12-1 mesi** (Jegadeesh & Titman 1993), "
        "**30% bassa volatilità** (Baker et al. 2011), **20% trend** (distanza dalla media "
        "a 200 giorni). Regolarità documentate in letteratura, non garanzie né consulenza.",
    ),
    "mkt.low_vol": ("Low volatility", "Bassa volatilità"),
    # ---------------------------------------------------------------- correlazioni
    "xc.title": ("Co-movement between securities", "Co-movimento tra titoli"),
    "xc.caption": (
        "Correlation of daily returns: **+1** = identical, **0** = independent, **-1** = opposite.",
        "Correlazione dei rendimenti giornalieri: **+1** = identici, **0** = indipendenti, **-1** = opposti.",
    ),
    "xc.reference": ("Reference security", "Titolo di riferimento"),
    "xc.reference_ph": ("Choose a Nasdaq-100 security", "Scegli un titolo del Nasdaq-100"),
    "xc.together": ("**Most correlated with {ticker}**", "**Più correlati con {ticker}**"),
    "xc.opposite": ("**Least correlated with {ticker}**", "**Meno correlati con {ticker}**"),
    "xc.portfolio": ("Portfolio diversification", "Diversificazione del portafoglio"),
    "xc.avg": ("Average pairwise correlation", "Correlazione media tra coppie"),
    "xc.tightest": (
        "Most correlated pair: **{a} / {b}** ({value})",
        "Coppia più correlata: **{a} / {b}** ({value})",
    ),
    # ---------------------------------------------------------------- backtest
    "bt.title": ("Strategy backtest", "Backtest delle strategie"),
    "bt.caption": (
        "Quarterly rebalancing, weights computed only on prior data (no look-ahead). "
        "Limits: USD prices, universe = CURRENT Nasdaq-100 constituents (survivorship bias).",
        "Ribilanciamento trimestrale, pesi calcolati solo su dati precedenti (nessun "
        "look-ahead). Limiti: prezzi in USD, universo = costituenti ATTUALI del Nasdaq-100 "
        "(survivorship bias).",
    ),
    "bt.strategies": ("Strategies to compare", "Strategie da confrontare"),
    "bt.s_equal": ("Equal-weight Nasdaq-100", "Nasdaq-100 equipesato"),
    "bt.s_momentum": ("Momentum (top 10, 6 months)", "Momentum (primi 10, 6 mesi)"),
    "bt.s_multifactor": ("Multifactor PI (top 10)", "Multifattoriale PI (primi 10)"),
    "bt.s_buy_hold": ("Current portfolio (buy and hold)", "Portafoglio attuale (buy and hold)"),
    "bt.s_max_sharpe": ("Maximum Sharpe on current holdings", "Massimo Sharpe sui titoli attuali"),
    "bt.s_min_var": ("Minimum variance on current holdings", "Minima varianza sui titoli attuali"),
    "bt.horizon": ("Horizon", "Orizzonte"),
    "bt.h_1y": ("1 year", "1 anno"),
    "bt.h_2y": ("2 years", "2 anni"),
    "bt.h_5y": ("5 years", "5 anni"),
    "bt.costs": (
        "Transaction costs (bps per rebalance)",
        "Costi di transazione (bps per ribilanciamento)",
    ),
    "bt.costs_help": (
        "20 bps = 0.20% of the traded value. Buy and hold pays only the initial purchase.",
        "20 bps = 0,20% del controvalore scambiato. Il buy and hold paga solo l'acquisto iniziale.",
    ),
    "bt.running": ("Running the backtests", "Calcolo dei backtest in corso"),
    "bt.col_strategy": ("Strategy", "Strategia"),
    "bt.col_return": ("Cumulative return", "Rendimento cumulato"),
    "bt.footer": (
        "Curves rebased to 100, {bps} bps cost per rebalance. Compare volatility and "
        "drawdown, not only return.",
        "Curve in base 100, costo di {bps} bps per ribilanciamento. Confronta volatilità "
        "e drawdown, non solo il rendimento.",
    ),
    # ---------------------------------------------------------------- amministrazione
    "adm.denied": (
        "Access denied: this section is for administrators only.",
        "Accesso negato: sezione riservata agli amministratori.",
    ),
    "adm.title": ("Platform (administrators only)", "Piattaforma (solo amministratori)"),
    "adm.caption": (
        "Cross-tenant counters and the audit log. Never shows the contents of another "
        "advisor's portfolios: only who did what, and when.",
        "Contatori tra consulenti e registro delle attività. Non mostra mai il contenuto "
        "dei portafogli di altri consulenti: solo chi ha fatto cosa, e quando.",
    ),
    "adm.no_auth": (
        "OIDC sign-in is not configured: tenant isolation is not guaranteed and these "
        "counters may refer to a shared development tenant.",
        "L'accesso OIDC non è configurato: l'isolamento tra consulenti non è garantito e "
        "questi contatori possono riferirsi a un ambiente di sviluppo condiviso.",
    ),
    "adm.advisors": ("Advisors", "Consulenti"),
    "adm.portfolios": ("Saved portfolios", "Portafogli salvati"),
    "adm.analyses": ("Logged analyses", "Analisi registrate"),
    "adm.last_sync": ("Last price update", "Ultimo aggiornamento prezzi"),
    "adm.activity": ("Recent activity (all tenants)", "Attività recente (tutti i consulenti)"),
    "adm.no_events": ("No audit events yet.", "Nessun evento registrato."),
    # ---------------------------------------------------------------- varie
    "opt.premium_delta": ("-{premium} premium", "-{premium} premio"),
    "chk.hist_risk": ("Risk /100", "Rischio /100"),
    "chk.hist_health": ("Health /100", "Health /100"),
    "chart.correlation": ("Correlation", "Correlazione"),
    "chart.return": ("Return", "Rendimento"),
    "chart.date": ("Date", "Data"),
    "chart.axis": ("Axis", "Asse"),
    "a11y.section": ("Section", "Sezione"),
    "a11y.subsection": ("Subsection", "Sottosezione"),
    "a11y.search_stock": ("Search stock", "Cerca titolo"),
    # settori (nomi SEC/Yahoo): tradotti al caricamento dei fondamentali
    "sector.Basic Materials": ("Basic Materials", "Materiali di base"),
    "sector.Communication Services": ("Communication Services", "Servizi di comunicazione"),
    "sector.Consumer Cyclical": ("Consumer Cyclical", "Beni di consumo ciclici"),
    "sector.Consumer Defensive": ("Consumer Defensive", "Beni di consumo difensivi"),
    "sector.Energy": ("Energy", "Energia"),
    "sector.Financial Services": ("Financial Services", "Servizi finanziari"),
    "sector.Healthcare": ("Healthcare", "Sanità"),
    "sector.Industrials": ("Industrials", "Industria"),
    "sector.Real Estate": ("Real Estate", "Immobiliare"),
    "sector.Technology": ("Technology", "Tecnologia"),
    "sector.Utilities": ("Utilities", "Servizi di pubblica utilità"),
    "chart.score": ("Score", "Punteggio"),
    "chart.value": ("Value", "Valore"),
    "chart.series": ("Series", "Serie"),
    "chart.from_peak": ("From peak", "Dal massimo"),
    # ---------------------------------------------------------------- panoramica Advisor
    "ov.asof": ("Prices as of {date}", "Prezzi al {date}"),
    "ov.ccy": ("Currency {ccy}", "Valuta {ccy}"),
    "ov.native_ccy": ("listing currency", "valuta di quotazione"),
    "ov.window": ("Window {period}", "Finestra {period}"),
    "ov.benchmark": ("Benchmark {benchmark}", "Benchmark {benchmark}"),
    "ov.kf_value": ("Market value", "Valore di mercato"),
    "ov.kf_value_sub": ("{n} positions at last price", "{n} posizioni all'ultimo prezzo"),
    "ov.kf_pnl": ("Unrealized P&L", "P&L non realizzato"),
    "ov.kf_pnl_sub": ("{pct} on cost of {cost}", "{pct} su un costo di {cost}"),
    "ov.kf_pnl_unknown": ("Cost basis not available", "Prezzo di carico non disponibile"),
    "ov.kf_irr": ("Money-weighted return", "Rendimento money-weighted"),
    "ov.kf_irr_sub": ("IRR p.a. on dated purchases", "IRR annuo sugli acquisti datati"),
    "ov.kf_return": ("Return {period}", "Rendimento {period}"),
    "ov.kf_bench": ("{benchmark}: {value}", "{benchmark}: {value}"),
    "ov.kf_vol": ("Volatility (ann.)", "Volatilità (ann.)"),
    "ov.kf_vol_sub": ("Profile limit {band}", "Limite del profilo {band}"),
    "ov.no_profile": ("Profile not declared", "Profilo non dichiarato"),
    "ov.kf_dd": ("Maximum drawdown", "Massimo drawdown"),
    "ov.kf_var": ("VaR 95%, 1 day", "VaR 95%, 1 giorno"),
    "ov.kf_var_sub": ("{pct} of value, historical", "{pct} del valore, storico"),
    "ov.kf_sharpe": ("Sharpe ratio", "Indice di Sharpe"),
    "ov.kf_sharpe_sub": ("Beta {beta} vs {benchmark}", "Beta {beta} vs {benchmark}"),
    "ov.perf_title": (
        "Performance vs {benchmark}, base 100",
        "Performance vs {benchmark}, base 100",
    ),
    "ov.perf_note": (
        "Current weights applied over the whole window: it describes the portfolio as "
        "held today, not the client's realized track record.",
        "Pesi attuali applicati a tutta la finestra: descrive il portafoglio come è "
        "detenuto oggi, non lo storico realizzato dal cliente.",
    ),
    "ov.monitor_title": ("Monitoring checks", "Controlli di monitoraggio"),
    "ov.monitor_breaches": (
        "{n} of {total} checks outside threshold",
        "{n} controlli su {total} fuori soglia",
    ),
    "ov.monitor_clear": (
        "All {total} checks within threshold",
        "Tutti i {total} controlli entro soglia",
    ),
    "ov.monitor_note": (
        "Internal monitoring thresholds, the same used in the report. They flag what to "
        "review and are not a suitability assessment under MiFID II.",
        "Soglie interne di monitoraggio, le stesse del report. Segnalano cosa rivedere e "
        "non sono una valutazione di adeguatezza ai sensi della MiFID II.",
    ),
    "ov.col_check": ("Check", "Controllo"),
    "ov.col_measured": ("Measured", "Misurato"),
    "ov.col_limit": ("Threshold", "Soglia"),
    "ov.col_status": ("Status", "Stato"),
    "ov.status_ok": ("Within", "Entro"),
    "ov.status_breach": ("Outside", "Fuori"),
    "ov.status_na": ("n/a", "n/d"),
    "ov.chk_profile_vol": ("Volatility vs profile", "Volatilità vs profilo"),
    "ov.chk_max_position": ("Largest position", "Prima posizione"),
    "ov.chk_risk_share": ("Largest risk contributor", "Primo contributore al rischio"),
    "ov.chk_correlation": ("Average correlation", "Correlazione media"),
    "ov.chk_usd": ("USD exposure", "Esposizione al dollaro"),
    "ov.chk_drawdown": ("Maximum drawdown", "Massimo drawdown"),
    "ov.chk_health": ("Health Score", "Health Score"),
    "ov.holdings_title": ("Holdings", "Posizioni"),
    "ov.holdings_note": (
        "Market value and P&L at the last available price; risk = share of portfolio "
        "variance explained by the position.",
        "Valore e P&L all'ultimo prezzo disponibile; rischio = quota della varianza del "
        "portafoglio spiegata dalla posizione.",
    ),
    "ov.export_csv": ("Export CSV", "Esporta CSV"),
    "ov.col_avg_cost": ("Avg. cost", "Prezzo medio"),
    "ov.col_last": ("Last price", "Ultimo prezzo"),
    "ov.col_value": ("Value ({ccy})", "Valore ({ccy})"),
    "ov.col_pnl": ("P&L ({ccy})", "P&L ({ccy})"),
    "ov.col_pnl_pct": ("P&L %", "P&L %"),
    "ov.col_risk": ("Risk share", "Quota di rischio"),
    "ov.obs_title": ("Observations", "Rilievi"),
    "ov.summary_title": ("Summary", "Sintesi"),
    "ov.sector_title": ("Allocation by sector", "Allocazione per settore"),
    "ov.scenario_title": ("Rebalancing scenarios", "Scenari di ribilanciamento"),
    "ov.reporting_title": ("Reports", "Report"),
    # ---------------------------------------------------------------- book clienti
    "adv.col_top": ("Largest", "Prima pos."),
    "adv.book_asof": (
        "Prices as of {date} · window {period} · values in EUR at the last price",
        "Prezzi al {date} · finestra {period} · valori in EUR all'ultimo prezzo",
    ),
    "adv.export_book": ("Export book (CSV)", "Esporta book (CSV)"),
    "adv.over_limit": (
        "Above the profile limit of {band}",
        "Oltre il limite del profilo ({band})",
    ),
    # ---------------------------------------------------------------- report: metriche e valutazioni
    "rpt.m_value": ("Portfolio value", "Valore del portafoglio"),
    "rpt.m_total_return": ("Total return", "Rendimento totale"),
    "rpt.m_cagr": ("CAGR", "CAGR"),
    "rpt.m_vol": ("Volatility (ann.)", "Volatilità (ann.)"),
    "rpt.m_vol_diff": ("Volatility differential", "Differenziale di volatilità"),
    "rpt.m_sharpe": ("Sharpe ratio", "Indice di Sharpe"),
    "rpt.m_sortino": ("Sortino ratio", "Indice di Sortino"),
    "rpt.m_maxdd": ("Maximum drawdown", "Massimo drawdown"),
    "rpt.m_var": ("VaR 95%, 1 day", "VaR 95%, 1 giorno"),
    "rpt.m_es": ("Expected Shortfall 95%", "Expected Shortfall 95%"),
    "rpt.m_beta": ("Beta vs {benchmark}", "Beta vs {benchmark}"),
    "rpt.m_alpha": ("Alpha (ann.)", "Alfa (ann.)"),
    "rpt.m_corr": ("Correlation with benchmark", "Correlazione con il benchmark"),
    "rpt.m_te": ("Tracking error", "Tracking error"),
    "rpt.m_ir": ("Information ratio", "Information ratio"),
    "rpt.m_capture": ("Up / down capture", "Up / down capture"),
    "rpt.m_hhi": ("Concentration (HHI)", "Concentrazione (HHI)"),
    "rpt.m_top": ("Largest position", "Prima posizione"),
    "rpt.m_usd": ("USD exposure", "Esposizione al dollaro"),
    "rpt.m_best_month": ("Best month", "Mese migliore"),
    "rpt.m_worst_month": ("Worst month", "Mese peggiore"),
    "rpt.a_value": (
        "Market value at the last available price",
        "Valore di mercato all'ultimo prezzo disponibile",
    ),
    "rpt.ret_better": ("Outperformed the benchmark by {pp}", "Sopra il benchmark di {pp}"),
    "rpt.ret_worse": ("Underperformed the benchmark by {pp}", "Sotto il benchmark di {pp}"),
    "rpt.ret_inline": ("In line with the benchmark", "In linea con il benchmark"),
    "rpt.vol_better": (
        "Lower volatility than the benchmark ({pp})",
        "Volatilità inferiore al benchmark ({pp})",
    ),
    "rpt.vol_worse": (
        "Higher volatility than the benchmark ({pp})",
        "Volatilità superiore al benchmark ({pp})",
    ),
    "rpt.vol_inline": (
        "Volatility in line with the benchmark",
        "Volatilità in linea con il benchmark",
    ),
    "rpt.dd_better": (
        "Shallower drawdown than the benchmark ({pp})",
        "Drawdown meno profondo del benchmark ({pp})",
    ),
    "rpt.dd_worse": (
        "Deeper drawdown than the benchmark ({pp})",
        "Drawdown più profondo del benchmark ({pp})",
    ),
    "rpt.dd_inline": ("Drawdown in line with the benchmark", "Drawdown in linea con il benchmark"),
    "rpt.tail_better": (
        "Smaller historical tail loss than the benchmark ({pp})",
        "Perdita di coda storica inferiore al benchmark ({pp})",
    ),
    "rpt.tail_worse": (
        "Larger historical tail loss than the benchmark ({pp})",
        "Perdita di coda storica superiore al benchmark ({pp})",
    ),
    "rpt.tail_inline": (
        "Tail loss in line with the benchmark",
        "Perdita di coda in linea con il benchmark",
    ),
    "rpt.sharpe_better": (
        "Higher return per unit of total risk",
        "Rendimento per unità di rischio totale più alto",
    ),
    "rpt.sharpe_worse": (
        "Lower return per unit of total risk",
        "Rendimento per unità di rischio totale più basso",
    ),
    "rpt.sharpe_inline": (
        "Risk-adjusted return in line",
        "Rendimento corretto per il rischio in linea",
    ),
    "rpt.sortino_better": (
        "Higher return per unit of downside risk",
        "Rendimento per unità di rischio al ribasso più alto",
    ),
    "rpt.sortino_worse": (
        "Lower return per unit of downside risk",
        "Rendimento per unità di rischio al ribasso più basso",
    ),
    "rpt.sortino_inline": (
        "Downside-adjusted return in line",
        "Rendimento corretto per il ribasso in linea",
    ),
    "rpt.beta_amplifies": (
        "Amplifies {benchmark} moves",
        "Amplifica i movimenti del benchmark {benchmark}",
    ),
    "rpt.beta_dampens": (
        "Dampens {benchmark} moves",
        "Attenua i movimenti del benchmark {benchmark}",
    ),
    "rpt.beta_inline": (
        "Broadly in line with {benchmark}",
        "Sostanzialmente in linea con il benchmark {benchmark}",
    ),
    "rpt.a_alpha": (
        "Regression intercept on daily data; historical, not evidence of skill",
        "Intercetta della regressione su dati giornalieri; storica, non prova di abilità",
    ),
    "rpt.a_corr": (
        "R² {r2}: share of daily variance explained by the benchmark",
        "R² {r2}: quota della varianza giornaliera spiegata dal benchmark",
    ),
    "rpt.te_high": (
        "High active risk versus the benchmark",
        "Rischio attivo elevato rispetto al benchmark",
    ),
    "rpt.te_moderate": (
        "Moderate active risk versus the benchmark",
        "Rischio attivo moderato rispetto al benchmark",
    ),
    "rpt.a_ir": (
        "Active return per unit of active risk; historical",
        "Rendimento attivo per unità di rischio attivo; storico",
    ),
    "rpt.capture_text": (
        "Followed {up} of benchmark gains and {down} of losses ({basis})",
        "Ha seguito il {up} dei rialzi e il {down} dei ribassi del benchmark ({basis})",
    ),
    "rpt.basis_monthly": ("monthly data", "dati mensili"),
    "rpt.basis_daily": ("daily data", "dati giornalieri"),
    "rpt.a_hhi": (
        "Equivalent to {n} equally weighted positions",
        "Equivale a {n} posizioni equipesate",
    ),
    "rpt.a_top": ("Accounts for {risk} of total risk", "Spiega il {risk} del rischio totale"),
    "rpt.a_usd": (
        "Translation risk for a euro-based investor",
        "Rischio di cambio per un investitore in euro",
    ),
    # ---------------------------------------------------------------- report: categorie di rischio
    "rpt.cat_market": ("Market risk", "Rischio di mercato"),
    "rpt.cat_concentration": ("Concentration risk", "Rischio di concentrazione"),
    "rpt.cat_factor": ("Factor / sector risk", "Rischio fattoriale / settoriale"),
    "rpt.cat_currency": ("Currency risk", "Rischio di cambio"),
    "rpt.cat_volatility": ("Volatility risk", "Rischio di volatilità"),
    "rpt.cat_drawdown": ("Drawdown risk", "Rischio di drawdown"),
    "rpt.cat_liquidity": ("Liquidity risk", "Rischio di liquidità"),
    "rpt.cat_valuation": ("Valuation risk", "Rischio di valutazione"),
    "rpt.level_low": ("Low", "Basso"),
    "rpt.level_moderate": ("Moderate", "Moderato"),
    "rpt.level_elevated": ("Elevated", "Elevato"),
    "rpt.level_high": ("High", "Alto"),
    "rpt.level_na": ("Not assessed", "Non valutato"),
    "rpt.r_market_measure": ("Beta {beta} vs {benchmark}", "Beta {beta} vs {benchmark}"),
    "rpt.r_market_evidence": (
        "Correlation {corr}; a 20% benchmark decline implies {drop} via beta",
        "Correlazione {corr}; un calo del 20% del benchmark implica {drop} tramite il beta",
    ),
    "rpt.r_conc_measure": (
        "HHI {hhi}, {n} effective positions",
        "HHI {hhi}, {n} posizioni effettive",
    ),
    "rpt.r_conc_evidence": (
        "{ticker}: {weight} of capital, {risk} of risk; top three {top3}",
        "{ticker}: {weight} del capitale, {risk} del rischio; prime tre {top3}",
    ),
    "rpt.r_factor_measure": (
        "Largest sector: {sector} {weight}",
        "Primo settore: {sector} {weight}",
    ),
    "rpt.r_factor_evidence": (
        "Sector known for {coverage} of capital (SEC SIC code or backup source)",
        "Settore noto per il {coverage} del capitale (codice SIC della SEC o fonte di riserva)",
    ),
    "rpt.r_fx_measure": ("USD-listed share {share}", "Quota quotata in USD {share}"),
    "rpt.r_fx_evidence": (
        "A 10% USD depreciation versus EUR implies about {impact} in EUR terms",
        "Un deprezzamento del 10% del dollaro sull'euro implica circa {impact} in euro",
    ),
    "rpt.r_fx_native": (
        "Figures in listing currency: translation effect not included",
        "Valori nella valuta di quotazione: effetto cambio non incluso",
    ),
    "rpt.r_vol_measure": ("Annualized volatility {vol}", "Volatilità annualizzata {vol}"),
    "rpt.r_vol_evidence": ("{benchmark}: {bench}", "{benchmark}: {bench}"),
    "rpt.r_dd_measure": ("Maximum drawdown {dd}", "Massimo drawdown {dd}"),
    "rpt.dd_open": (
        "Peak {peak}, trough {trough}; not yet recovered, currently {current} from the peak",
        "Massimo {peak}, minimo {trough}; non ancora recuperato, oggi a {current} dal massimo",
    ),
    "rpt.dd_recovered": (
        "Peak {peak}, trough {trough}; recovered in {days} days after the trough",
        "Massimo {peak}, minimo {trough}; recuperato in {days} giorni dal minimo",
    ),
    "rpt.r_liq_measure": ("Not measured", "Non misurato"),
    "rpt.r_liq_evidence": (
        "Trading volumes and bid-ask spreads are not in the dataset: liquidity is not assessed",
        "Volumi e spread denaro-lettera non sono nei dati: la liquidità non è valutata",
    ),
    "rpt.r_val_measure": ("Weighted P/E {pe}", "P/E ponderato {pe}"),
    "rpt.r_val_missing": ("P/E not available", "P/E non disponibile"),
    "rpt.r_val_evidence": (
        "Harmonic weighted trailing P/E; coverage {coverage} of capital",
        "P/E storico, media armonica ponderata; copertura {coverage} del capitale",
    ),
    # ---------------------------------------------------------------- report: vista d'investimento
    "rpt.vh_positioning": ("Portfolio positioning", "Posizionamento del portafoglio"),
    "rpt.vh_regime": ("Risk regime", "Regime di rischio"),
    "rpt.vh_performance": ("Performance versus benchmark", "Performance rispetto al benchmark"),
    "rpt.vh_concentration": ("Principal concentration", "Concentrazione principale"),
    "rpt.vh_sources": ("Principal sources of risk", "Principali fonti di rischio"),
    "rpt.vh_vulnerabilities": ("Key vulnerabilities", "Vulnerabilità principali"),
    "rpt.vh_strengths": ("Key strengths", "Punti di forza"),
    "rpt.vh_implications": ("Material investment implications", "Implicazioni rilevanti"),
    "rpt.v_positioning": (
        "{n} positions, equivalent to {eff} equally weighted holdings. Largest sector {sector} "
        "at {sector_w} of capital; {usd} of capital is listed in USD.",
        "{n} posizioni, equivalenti a {eff} posizioni equipesate. Primo settore {sector} con "
        "il {sector_w} del capitale; il {usd} del capitale è quotato in USD.",
    ),
    "rpt.v_regime": (
        "Annualized volatility {vol} ({level}) against {bench_vol} for {benchmark}; beta "
        "{beta}; maximum drawdown {dd} over the window.",
        "Volatilità annualizzata {vol} ({level}) contro {bench_vol} del benchmark {benchmark}; beta "
        "{beta}; massimo drawdown {dd} nella finestra.",
    ),
    "rpt.v_performance": (
        "Applying today's weights from {start} to {end}, the portfolio would have returned {ret} against {bench} for {benchmark} ({excess}); CAGR {cagr} versus {bench_cagr}; Sharpe {sharpe} versus {bench_sharpe}.",
        "Applicando i pesi di oggi dal {start} al {end}, il portafoglio avrebbe reso {ret} contro {bench} del benchmark {benchmark} ({excess}); CAGR {cagr} contro {bench_cagr}; Sharpe {sharpe} contro {bench_sharpe}.",
    ),
    "rpt.v_concentration": (
        "{ticker} represents {weight} of capital and {risk} of total risk; the three largest "
        "positions account for {top3}.",
        "{ticker} rappresenta il {weight} del capitale e il {risk} del rischio totale; le tre "
        "posizioni maggiori valgono il {top3}.",
    ),
    "rpt.v_source_position": (
        "{ticker}: {share} of portfolio variance.",
        "{ticker}: {share} della varianza del portafoglio.",
    ),
    "rpt.v_source_market": (
        "Market factor: {r2} of daily variance explained by {benchmark}.",
        "Fattore di mercato: il {r2} della varianza giornaliera è spiegato dal benchmark {benchmark}.",
    ),
    "rpt.v_vuln_risk_weight": (
        "{ticker} contributes {risk} of risk on a {weight} capital weight.",
        "{ticker} contribuisce il {risk} del rischio con un peso del {weight} sul capitale.",
    ),
    "rpt.v_vuln_profile": (
        "Measured volatility {vol} exceeds the {band} band associated with the declared "
        "{profile} profile.",
        "La volatilità misurata {vol} supera la banda del {band} associata al profilo "
        "dichiarato {profile}.",
    ),
    "rpt.v_vuln_down_capture": (
        "Down capture {down}: in falling periods the portfolio lost more than the benchmark.",
        "Down capture {down}: nei periodi di ribasso il portafoglio ha perso più del benchmark.",
    ),
    "rpt.v_vuln_sector": (
        "Sector concentration: {sector} accounts for {weight} of capital.",
        "Concentrazione settoriale: {sector} vale il {weight} del capitale.",
    ),
    "rpt.v_vuln_open_dd": (
        "The deepest drawdown is not yet recovered: value is {current} from its peak.",
        "Il drawdown più profondo non è ancora recuperato: il valore è a {current} dal massimo.",
    ),
    "rpt.v_vuln_valuation": (
        "Weighted trailing P/E {pe}, above the 40 reference level.",
        "P/E storico ponderato {pe}, sopra il livello di riferimento di 40.",
    ),
    "rpt.v_none": (
        "No rule triggered on the available data.",
        "Nessuna regola scattata sui dati disponibili.",
    ),
    "rpt.v_str_sharpe": (
        "Sharpe ratio {sharpe} above the benchmark's {bench}.",
        "Indice di Sharpe {sharpe} superiore al {bench} del benchmark.",
    ),
    "rpt.v_str_dd": (
        "Maximum drawdown {dd} shallower than the benchmark's {bench}.",
        "Massimo drawdown {dd} meno profondo del {bench} del benchmark.",
    ),
    "rpt.v_str_down_capture": (
        "Down capture {down}: losses smaller than the benchmark's in falling periods.",
        "Down capture {down}: perdite inferiori al benchmark nei periodi di ribasso.",
    ),
    "rpt.v_str_diversified": (
        "Broad diversification: {n} effective positions.",
        "Diversificazione ampia: {n} posizioni effettive.",
    ),
    "rpt.v_str_low_corr": (
        "Correlation {corr} with {benchmark}: return drivers differ from the benchmark.",
        "Correlazione {corr} con il benchmark {benchmark}: i fattori di rendimento differiscono dai suoi.",
    ),
    "rpt.v_impl_driver": (
        "Portfolio outcomes depend primarily on {ticker}, which explains {risk} of total risk.",
        "Il risultato del portafoglio dipende soprattutto da {ticker}, che spiega il {risk} del rischio totale.",
    ),
    "rpt.v_impl_market": (
        "On the historical beta, a 20% decline in {benchmark} corresponds to about {impact} for the portfolio.",
        "Sul beta storico, un calo del 20% del benchmark {benchmark} corrisponde a circa {impact} per il portafoglio.",
    ),
    "rpt.v_impl_profile_out": (
        "Consistency with the declared {profile} profile ({band} volatility band) requires review.",
        "La coerenza con il profilo dichiarato {profile} (banda di volatilità {band}) va verificata.",
    ),
    "rpt.v_impl_profile_in": (
        "Measured volatility is within the {band} band of the declared {profile} profile.",
        "La volatilità misurata è entro la banda del {band} del profilo dichiarato {profile}.",
    ),
    "rpt.v_impl_alpha": (
        "Historical alpha and excess return describe the window observed; they are not "
        "evidence of persistent skill.",
        "Alfa ed extra-rendimento storici descrivono la finestra osservata; non sono prova "
        "di un'abilità persistente.",
    ),
    # ---------------------------------------------------------------- report: performance e recupero
    "rpt.pb_absolute": ("Absolute performance", "Performance assoluta"),
    "rpt.pb_relative": ("Benchmark-relative performance", "Performance relativa al benchmark"),
    "rpt.pb_risk_adjusted": ("Risk-adjusted performance", "Performance corretta per il rischio"),
    "rpt.recovery_open": (
        "Deepest drawdown {dd}: peak {peak}, trough {trough} after {days} days; not yet "
        "recovered (currently {current} from the peak).",
        "Drawdown più profondo {dd}: massimo il {peak}, minimo il {trough} dopo {days} giorni; "
        "non ancora recuperato (oggi a {current} dal massimo).",
    ),
    "rpt.recovery_done": (
        "Deepest drawdown {dd}: peak {peak}, trough {trough} after {days} days; previous peak "
        "regained on {recovery}, {rdays} days after the trough.",
        "Drawdown più profondo {dd}: massimo il {peak}, minimo il {trough} dopo {days} giorni; "
        "massimo precedente recuperato il {recovery}, {rdays} giorni dopo il minimo.",
    ),
    # ---------------------------------------------------------------- report: punti di revisione
    "rpt.rp_profile": (
        "Profile consistency: measured volatility {vol} versus the {band} band of the "
        "declared {profile} profile.",
        "Coerenza con il profilo: volatilità misurata {vol} contro la banda del {band} del "
        "profilo dichiarato {profile}.",
    ),
    "rpt.rp_no_profile": (
        "No risk profile declared for this client: profile consistency cannot be checked.",
        "Nessun profilo di rischio dichiarato per il cliente: la coerenza non è verificabile.",
    ),
    "rpt.rp_concentration": (
        "Single-name concentration: {ticker} at {weight} of capital, above the 25% reference.",
        "Concentrazione su un singolo titolo: {ticker} al {weight} del capitale, oltre il riferimento del 25%.",
    ),
    "rpt.rp_risk_weight": (
        "{ticker}: risk share {risk} against a {weight} capital weight.",
        "{ticker}: quota di rischio {risk} contro un peso del {weight} sul capitale.",
    ),
    "rpt.rp_currency": (
        "Currency exposure: {share} of capital in USD-listed securities; any currency hedging is not captured in the data.",
        "Esposizione valutaria: il {share} del capitale in titoli quotati in USD; eventuali coperture valutarie non sono rilevate nei dati.",
    ),
    "rpt.rp_sector": (
        "Sector exposure: {sector} at {weight} of capital.",
        "Esposizione settoriale: {sector} al {weight} del capitale.",
    ),
    "rpt.rp_short_window": (
        "Observation window shorter than one year: annualized figures are indicative.",
        "Finestra di osservazione inferiore a un anno: i valori annualizzati sono indicativi.",
    ),
    "rpt.rp_none": (
        "No item flagged by the monitored rules.",
        "Nessun punto segnalato dalle regole monitorate.",
    ),
    # ---------------------------------------------------------------- report: elementi comuni
    "rep.page": ("Page {n} of {total}", "Pagina {n} di {total}"),
    "rep.footer1": (
        "SmarteeFinance · Portfolio Intelligence · Ref. {rid} · data sources in the methodology "
        "notes; accuracy and completeness not guaranteed",
        "SmarteeFinance · Portfolio Intelligence · Rif. {rid} · fonti dei dati nelle note di "
        "metodologia; accuratezza e completezza non garantite",
    ),
    "rep.source_unknown": (
        "provider chain (EODHD where licensed, Yahoo, yfinance, Stooq)",
        "catena di fornitori (EODHD se attivo, Yahoo, yfinance, Stooq)",
    ),
    "rep.mc_p10": ("Bear scenario (10th percentile)", "Scenario ribassista (10° percentile)"),
    "rep.mc_p50": ("Base scenario (median)", "Scenario centrale (mediana)"),
    "rep.mc_p90": ("Bull scenario (90th percentile)", "Scenario rialzista (90° percentile)"),
    "rep.mc_method_bootstrap": (
        "historical block bootstrap of joint daily returns (5-day blocks)",
        "bootstrap storico a blocchi dei rendimenti giornalieri congiunti (blocchi di 5 giorni)",
    ),
    "rep.mc_method_gbm": (
        "geometric Brownian motion calibrated on the historical mean and covariance",
        "moto browniano geometrico calibrato su media e covarianza storiche",
    ),
    "rep.mc_method": (
        "Method: {method}; {n} simulations; history {start} to {end}; constant current weights "
        "(daily rebalancing); no transaction costs, fees, taxes, contributions or withdrawals. "
        "Share of simulations ending below today's value after {horizon} years: {loss}. A "
        "statistical scenario derived from history, not a forecast or a guarantee.",
        "Metodo: {method}; {n} simulazioni; storico dal {start} al {end}; pesi attuali costanti "
        "(ribilanciamento giornaliero); senza costi di transazione, commissioni, imposte, "
        "versamenti o prelievi. Quota di simulazioni sotto il valore di oggi dopo {horizon} anni: "
        "{loss}. Uno scenario statistico ricavato dallo storico, non una previsione né una garanzia.",
    ),
    "rep.n_data": (
        "Prices: daily adjusted closes over the selected window ({period}) from {source}; "
        "dividends and splits are reflected through price adjustment. Data are provided as-is; "
        "accuracy, completeness and timeliness are not guaranteed.",
        "Prezzi: chiusure giornaliere rettificate nella finestra selezionata ({period}) da "
        "{source}; dividendi e frazionamenti sono riflessi tramite la rettifica dei prezzi. Dati "
        "forniti così come sono; accuratezza, completezza e tempestività non garantite.",
    ),
    "rep.n_fundamentals": (
        "Fundamentals and sectors: SEC EDGAR filings (last twelve months; sector from the SIC code), backup sources where unavailable; holdings without a sector are shown as not classified. EUR/USD: European Central Bank reference rates, backup source where unavailable. Geographic exposure: not available in the dataset; listing currency is shown instead.",
        "Fondamentali e settori: depositi SEC EDGAR (ultimi dodici mesi; settore dal codice SIC), fonti di riserva dove non disponibili; i titoli senza settore figurano come non classificati. EUR/USD: cambi di riferimento della Banca Centrale Europea, fonte di riserva dove non disponibili. Esposizione geografica: non disponibile nei dati; è indicata la valuta di quotazione.",
    ),
    "pdf.notice_rf2": (
        " ({rate}, as set in the analysis parameters; default source US Treasury 13-week bill)",
        " ({rate}, come impostato nei parametri di analisi; fonte predefinita T-bill a 13 settimane del Tesoro USA)",
    ),
    "rep.n_returns": (
        "Returns are geometric (CAGR), never arithmetic-mean annualization. Sharpe and "
        "Sortino use the excess return over the risk-free rate{rf}; Sortino penalizes "
        "downside deviation only.",
        "I rendimenti sono geometrici (CAGR), mai annualizzazione a media aritmetica. Sharpe "
        "e Sortino usano l'extra-rendimento sul tasso privo di rischio{rf}; il Sortino "
        "penalizza solo la deviazione al ribasso.",
    ),
    "rep.n_risk": (
        "VaR 95%: historical 5th percentile of daily returns, no normality assumed; Expected "
        "Shortfall: average of the returns beyond it. Beta and alpha: OLS regression of daily "
        "portfolio returns on {benchmark}. Tracking error: annualized standard deviation of "
        "daily active returns. Risk contribution: share of portfolio variance per position, "
        "covariances included.",
        "VaR 95%: 5° percentile storico dei rendimenti giornalieri, nessuna ipotesi di "
        "normalità; Expected Shortfall: media dei rendimenti oltre la soglia. Beta e alfa: "
        "regressione OLS dei rendimenti giornalieri del portafoglio sul benchmark {benchmark}. Tracking "
        "error: deviazione standard annualizzata dei rendimenti attivi giornalieri. Contributo "
        "al rischio: quota della varianza del portafoglio per posizione, covarianze incluse.",
    ),
    "rep.n_bench": (
        "Benchmark: {name}. Total return series: the ETF price includes dividends. Returns are "
        "net of the fund's costs and of any withholding tax the fund pays on dividends, while "
        "portfolio prices reinvest gross dividends, so relative performance and alpha against "
        "the benchmark may be slightly overstated.",
        "Benchmark: {name}. Serie total return: il prezzo dell'ETF include i dividendi. I "
        "rendimenti sono al netto dei costi del fondo e delle eventuali ritenute che il fondo "
        "subisce sui dividendi, mentre i prezzi del portafoglio reinvestono i dividendi lordi: "
        "rendimento relativo e alfa rispetto al benchmark possono risultare leggermente "
        "sovrastimati.",
    ),
    "rep.n_weights": (
        "Historical series apply today's weights to the whole window (constant weights): they "
        "describe the portfolio as currently held, not the realized track record.",
        "Le serie storiche applicano i pesi di oggi a tutta la finestra (pesi costanti): "
        "descrivono il portafoglio come è detenuto oggi, non lo storico realizzato.",
    ),
    "rep.n_scenarios": (
        "Stress tests and scenarios are statistical estimates on historical data, gross of "
        "costs and taxes: they are not forecasts and do not express an expected outcome.",
        "Stress test e scenari sono stime statistiche su dati storici, al lordo di costi e "
        "imposte: non sono previsioni e non esprimono un risultato atteso.",
    ),
    "rep.n_score": (
        "The Portfolio Health Score is a proprietary analytical composite (simple average of up to six components scored 0-100; components without data are excluded); it is not a rating, a regulated indicator or a suitability assessment.",
        "Il Portfolio Health Score è un indicatore composito proprietario (media semplice di fino a sei componenti valutate 0-100; quelle senza dati sono escluse); non è un rating, un indicatore regolamentato né una valutazione di adeguatezza.",
    ),
    "rep.n_personal_use": (
        "Generated for the personal information of the portfolio holder; not intended for "
        "public distribution.",
        "Generato per l'informazione personale del titolare del portafoglio; non destinato "
        "alla distribuzione al pubblico.",
    ),
    "stress.top_position": (
        "{ticker} ({weight} of capital) declines 20%",
        "{ticker} ({weight} del capitale) perde il 20%",
    ),
    "stress.market": (
        "{benchmark} declines 20% (beta-implied)",
        "Il benchmark {benchmark} perde il 20% (stima tramite beta)",
    ),
    "stress.usd": (
        "USD depreciates 10% versus EUR ({share} of capital in USD)",
        "Il dollaro perde il 10% sull'euro ({share} del capitale in USD)",
    ),
    "stress.worst_month": (
        "Worst observed month, replayed with current weights",
        "Peggior mese osservato, rigiocato con i pesi attuali",
    ),
    # ---------------------------------------------------------------- report Investor
    "inv.doc_title": (
        "SmarteeFinance · Portfolio Report",
        "SmarteeFinance · Report di Portafoglio",
    ),
    "inv.title": ("Portfolio Report", "Report di Portafoglio"),
    "inv.s_overview": ("Portfolio overview", "Panoramica del portafoglio"),
    "inv.k_value": ("Current value", "Valore attuale"),
    "inv.k_value_note": ("{n} positions at last price", "{n} posizioni all'ultimo prezzo"),
    "inv.k_invested": ("Invested capital", "Capitale investito"),
    "inv.k_invested_note": (
        "Cost basis of current positions",
        "Costo di carico delle posizioni attuali",
    ),
    "inv.k_cost_unknown": ("Cost basis not available", "Prezzo di carico non disponibile"),
    "inv.k_pnl": ("Unrealized P&L", "P&L non realizzato"),
    "inv.k_total_return": (
        "Return, current weights ({period})",
        "Rendimento a pesi attuali ({period})",
    ),
    "inv.k_window": ("{start} to {end}", "dal {start} al {end}"),
    "inv.k_bench": ("{benchmark}: {value}", "{benchmark}: {value}"),
    "inv.k_corr": ("Correlation {corr}", "Correlazione {corr}"),
    "inv.k_alpha_note": ("Historical, regression-based", "Storico, da regressione"),
    "inv.k_concentration": ("Concentration", "Concentrazione"),
    "inv.k_hhi": ("HHI {hhi}", "HHI {hhi}"),
    "inv.k_concentration_note": (
        "{n} effective positions; {ticker} {weight}",
        "{n} posizioni effettive; {ticker} {weight}",
    ),
    "inv.k_bench_return": ("Benchmark return", "Rendimento del benchmark"),
    "inv.k_bench_note": ("{benchmark}, same window", "{benchmark}, stessa finestra"),
    "inv.k_relative": ("Relative performance", "Performance relativa"),
    "inv.k_relative_note": (
        "Versus {benchmark}, percentage points",
        "Rispetto al benchmark {benchmark}, punti percentuali",
    ),
    "inv.score_line": (
        "<b>PORTFOLIO HEALTH SCORE: {score}/100</b>",
        "<b>PORTFOLIO HEALTH SCORE: {score}/100</b>",
    ),
    "inv.score_caption": (
        "Proprietary composite indicator based on diversification, concentration, volatility, "
        "currency exposure, drawdown and portfolio quality; higher means more balanced. Not a "
        "rating or a suitability assessment.",
        "Indicatore composito proprietario basato su diversificazione, concentrazione, "
        "volatilità, esposizione valutaria, drawdown e qualità del portafoglio; più alto "
        "significa più equilibrato. Non è un rating né una valutazione di adeguatezza.",
    ),
    "inv.profile_check": (
        "<b>Risk profile check: {status}.</b> Measured annualized volatility {vol} against the {band} band associated with a {profile} profile.",
        "<b>Verifica del profilo di rischio: {status}.</b> Volatilità annualizzata misurata {vol} contro la banda del {band} associata a un profilo {profile}.",
    ),
    "inv.s_summary": ("Executive summary", "Sintesi"),
    "inv.s_growth": (
        "Growth of 100 versus {benchmark}",
        "Crescita di 100 rispetto al benchmark {benchmark}",
    ),
    "inv.growth_caption": (
        "Both series rebased to 100 at the start of the window. The portfolio line applies "
        "today's weights to the whole window: it is not the realized track record.",
        "Entrambe le serie in base 100 all'inizio della finestra. La linea del portafoglio "
        "applica i pesi di oggi a tutta la finestra: non è lo storico realizzato.",
    ),
    "inv.p2_title": (
        "Performance and benchmark ({benchmark})",
        "Performance e benchmark ({benchmark})",
    ),
    "inv.h_difference": ("Difference", "Differenza"),
    "inv.alpha_caveat": (
        "Alpha, excess return and information ratio describe the window observed. They do not "
        "demonstrate investment skill and are not indicative of future results.",
        "Alfa, extra-rendimento e information ratio descrivono la finestra osservata. Non "
        "dimostrano abilità d'investimento e non sono indicativi dei risultati futuri.",
    ),
    "inv.s_recovery": (
        "Drawdown and recovery characteristics",
        "Drawdown e caratteristiche di recupero",
    ),
    "inv.s_score": ("Composite score components", "Componenti del punteggio composito"),
    "inv.score_components_text": (
        "Each component is scored 0-100 from the measured data; the Portfolio Health Score ({score}/100) is the simple average of the components available. Colour bands: green 67 and above, amber 34 to 66, red 33 and below. Proprietary methodology.",
        "Ogni componente vale 0-100 a partire dai dati misurati; il Portfolio Health Score ({score}/100) è la media semplice delle componenti disponibili. Fasce di colore: verde da 67, ambra da 34 a 66, rosso fino a 33. Metodologia proprietaria.",
    ),
    "inv.p3_title": ("Portfolio composition and risk", "Composizione e rischio del portafoglio"),
    "inv.s_holdings": (
        "Holdings: capital weight and risk contribution",
        "Posizioni: peso sul capitale e contributo al rischio",
    ),
    "inv.h_value": ("Value", "Valore"),
    "inv.h_weight": ("Capital wt.", "Peso cap."),
    "inv.h_risk": ("Risk contr.", "Contr. rischio"),
    "inv.h_ratio": ("Risk/weight", "Rischio/peso"),
    "inv.holdings_caption": (
        "Risk contribution: share of portfolio variance explained by the position, "
        "covariances included. Ratios above 1.25× are highlighted: the position weighs on "
        "risk materially more than on capital.",
        "Contributo al rischio: quota della varianza del portafoglio spiegata dalla "
        "posizione, covarianze incluse. I rapporti oltre 1,25× sono evidenziati: la "
        "posizione pesa sul rischio molto più che sul capitale.",
    ),
    "inv.eff_note": ("1 / HHI", "1 / HHI"),
    "inv.c_top3": ("Top 3 positions", "Prime 3 posizioni"),
    "inv.c_sector": ("Largest sector", "Primo settore"),
    "inv.sector_caption": (
        "Sector from the SEC SIC code, weighted by capital.",
        "Settore dal codice SIC della SEC, pesato per capitale.",
    ),
    "inv.s_risk": ("Risk analysis", "Analisi dei rischi"),
    "inv.h_category": ("Category", "Categoria"),
    "inv.h_measure": ("Measure", "Misura"),
    "inv.h_level": ("Level", "Livello"),
    "inv.h_evidence": ("Evidence", "Evidenza"),
    "inv.risk_caption": (
        "Levels from fixed thresholds on the measured data (methodology notes). Liquidity is "
        "not assessed: volumes and bid-ask spreads are not in the dataset.",
        "Livelli da soglie fisse sui dati misurati (note di metodologia). La liquidità non è "
        "valutata: volumi e spread denaro-lettera non sono nei dati.",
    ),
    "inv.p4_title": (
        "Stress testing, scenarios and methodology",
        "Stress test, scenari e metodologia",
    ),
    "inv.s_stress": ("Stress testing", "Stress test"),
    "inv.h_scenario": ("Scenario", "Scenario"),
    "inv.h_direct": ("Direct impact", "Impatto diretto"),
    "inv.h_total": ("Correlation-adjusted", "Corretto per correlazioni"),
    "inv.h_amount": ("Amount", "Importo"),
    "inv.stress_caption": (
        "Direct impact: the shocked position or currency share only. Correlation-adjusted: "
        "includes the historical co-movement of the other positions (betas over the window). "
        "Estimates, not forecasts.",
        "Impatto diretto: solo la posizione o la quota valutaria colpita. Corretto per "
        "correlazioni: include il co-movimento storico delle altre posizioni (beta nella "
        "finestra). Stime, non previsioni.",
    ),
    "inv.s_scenarios": (
        "Scenario analysis: historical 12-month outcomes",
        "Analisi di scenario: esiti storici a 12 mesi",
    ),
    "inv.h_12m_return": (
        "Observed 12-month return",
        "Rendimento osservato a 12 mesi",
    ),
    "inv.h_value_after": ("Value after 12 months", "Valore dopo 12 mesi"),
    "inv.sc_bear": (
        "Historical 5th percentile (bear)",
        "5° percentile storico (ribassista)",
    ),
    "inv.sc_base": (
        "Historical median (base)",
        "Mediana storica (centrale)",
    ),
    "inv.sc_bull": (
        "Historical 95th percentile (bull)",
        "95° percentile storico (rialzista)",
    ),
    "inv.sc_method": (
        "Distribution of all {windows} overlapping 12-month windows between {start} and {end} (days on which every current holding was priced), with today's weights held constant; gross of costs, fees and taxes. {negative} of windows closed with a loss; range {worst} to {best}. Historical statistics, not a forecast.",
        "Distribuzione di tutte le {windows} finestre sovrapposte di 12 mesi tra il {start} e il {end} (giorni in cui tutti i titoli attuali erano quotati), con i pesi di oggi costanti; al lordo di costi, commissioni e imposte. Il {negative} delle finestre si è chiuso in perdita; intervallo da {worst} a {best}. Statistiche storiche, non una previsione.",
    ),
    "inv.sc_short": (
        "Fewer than 13 months of history: 12-month scenarios are not computed.",
        "Meno di 13 mesi di storico: gli scenari a 12 mesi non vengono calcolati.",
    ),
    "inv.s_projection": (
        "Probabilistic projection (Monte Carlo)",
        "Proiezione probabilistica (Monte Carlo)",
    ),
    "inv.obs_caption": (
        "Generated by deterministic rules on the computed metrics. Descriptive, not a "
        "personalized recommendation.",
        "Generati da regole deterministiche sulle metriche calcolate. Descrittivi, non una "
        "raccomandazione personalizzata.",
    ),
    # ---------------------------------------------------------------- report Advisor
    "adr.doc_title": (
        "SmarteeFinance · Portfolio Review",
        "SmarteeFinance · Revisione di Portafoglio",
    ),
    "adr.title": ("Portfolio Review", "Revisione di Portafoglio"),
    "adr.subtitle": (
        "Advisor working document: institutional portfolio analytics and suitability context",
        "Documento di lavoro per il consulente: analisi istituzionale del portafoglio e contesto di adeguatezza",
    ),
    "adr.cover_note": (
        "Prepared as working material for the professional advisor. For the client, use the "
        "Portfolio Report.",
        "Predisposto come materiale di lavoro per il consulente. Per il cliente usare il "
        "Report di Portafoglio.",
    ),
    "adr.f_client": ("Client code", "Codice cliente"),
    "adr.f_recipient": ("Prepared for", "Preparato per"),
    "adr.f_advisor": ("Prepared by", "Predisposto da"),
    "adr.f_profile": ("Declared risk profile", "Profilo di rischio dichiarato"),
    "adr.f_valuation": ("Valuation date", "Data di valutazione"),
    "adr.f_window": ("Observation window", "Finestra di osservazione"),
    "adr.window_value": (
        "{start} to {end} ({n} trading days)",
        "dal {start} al {end} ({n} giorni di borsa)",
    ),
    "adr.f_benchmark": ("Benchmark", "Benchmark"),
    "adr.f_currency": ("Currency basis", "Base valutaria"),
    "adr.f_source": ("Price source", "Fonte prezzi"),
    "adr.f_reference": ("Document reference", "Riferimento documento"),
    "adr.s1": ("Executive investment view", "Sintesi d'investimento"),
    "adr.s1_caption": (
        "Every statement is generated by deterministic rules from the portfolio data cited in it; no language model is involved. Return figures apply current weights to past prices; historical alpha and excess return are not evidence of persistent skill.",
        "Ogni frase è generata da regole deterministiche a partire dai dati che cita; nessun modello linguistico è coinvolto. I rendimenti applicano i pesi attuali ai prezzi passati; alfa ed extra-rendimento storici non sono prova di un'abilità persistente.",
    ),
    "adr.s2": ("Portfolio profile", "Profilo del portafoglio"),
    "adr.h_assessment": ("Assessment", "Valutazione"),
    "adr.s2_caption": (
        "Benchmark: {benchmark} over the same window and currency basis. Capture ratios: "
        "average portfolio return in benchmark up (down) periods over the average benchmark "
        "return in those periods.",
        "Benchmark: {benchmark} sulla stessa finestra e base valutaria. Capture ratio: "
        "rendimento medio del portafoglio nei periodi di rialzo (ribasso) del benchmark "
        "diviso per il rendimento medio del benchmark negli stessi periodi.",
    ),
    "adr.s3": ("Performance analysis", "Analisi della performance"),
    "adr.monthly_title": ("Last twelve months", "Ultimi dodici mesi"),
    "adr.h_month": ("Month", "Mese"),
    "adr.episodes_title": ("Largest drawdown episodes", "Episodi di drawdown più profondi"),
    "adr.h_peak": ("Peak", "Massimo"),
    "adr.h_trough": ("Trough", "Minimo"),
    "adr.h_depth": ("Depth", "Profondità"),
    "adr.h_to_trough": ("Days to trough", "Giorni al minimo"),
    "adr.h_recovery": ("Recovered", "Recuperato"),
    "adr.h_to_recover": ("Days to recover", "Giorni al recupero"),
    "adr.not_recovered": ("Not yet", "Non ancora"),
    "adr.attribution_title": (
        "Return attribution by position",
        "Attribuzione del rendimento per posizione",
    ),
    "adr.h_contribution": ("Contribution", "Contributo"),
    "adr.attribution_caption": (
        "Current weight × security return over the window; an approximation that ignores "
        "intra-period weight drift.",
        "Peso attuale × rendimento del titolo nella finestra; approssimazione che ignora la "
        "deriva dei pesi nel periodo.",
    ),
    "adr.s4": ("Composition and concentration", "Composizione e concentrazione"),
    "adr.h_sector": ("Sector", "Settore"),
    "adr.currency_title": ("Currency of listing", "Valuta di quotazione"),
    "adr.ccy_usd": ("USD", "USD"),
    "adr.ccy_other": ("EUR and other", "EUR e altre"),
    "adr.flagged": (
        "Risk contribution materially above capital weight (ratio above 1.25×): {tickers}.",
        "Contributo al rischio molto superiore al peso sul capitale (rapporto oltre 1,25×): {tickers}.",
    ),
    "adr.flagged_none": (
        "No position has a risk contribution above 1.25 times its capital weight.",
        "Nessuna posizione ha un contributo al rischio oltre 1,25 volte il peso sul capitale.",
    ),
    "adr.s5": ("Risk analysis", "Analisi dei rischi"),
    "adr.s6": ("Stress testing", "Stress test"),
    "adr.stress_note": (
        "The market scenario applies the portfolio beta to a 20% benchmark decline; the "
        "currency scenario is a translation effect on the USD-listed share and ignores any "
        "correlation between currency and equity prices.",
        "Lo scenario di mercato applica il beta del portafoglio a un calo del 20% del "
        "benchmark; lo scenario valutario è un effetto di traduzione sulla quota quotata in "
        "USD e ignora la correlazione tra cambio e prezzi azionari.",
    ),
    "adr.s7": ("Scenario analysis", "Analisi di scenario"),
    "adr.mc_f_method": ("Methodology", "Metodologia"),
    "adr.mc_f_sims": ("Number of simulations", "Numero di simulazioni"),
    "adr.mc_f_history": ("Historical period", "Periodo storico"),
    "adr.mc_f_weights": ("Weights", "Pesi"),
    "adr.mc_v_weights": (
        "Current weights held constant (daily rebalancing)",
        "Pesi attuali mantenuti costanti (ribilanciamento giornaliero)",
    ),
    "adr.mc_f_costs": ("Costs, fees and taxes", "Costi, commissioni e imposte"),
    "adr.mc_v_costs": (
        "Excluded; no contributions or withdrawals",
        "Esclusi; nessun versamento o prelievo",
    ),
    "adr.mc_f_nature": ("Nature of the output", "Natura del risultato"),
    "adr.mc_v_nature": (
        "Statistical scenario derived from history; not a forecast",
        "Scenario statistico ricavato dallo storico; non una previsione",
    ),
    "adr.year_tick": ("Year {n}", "Anno {n}"),
    "adr.fan_caption": (
        "Dark band: 25th to 75th percentile; light band: 10th to 90th; line: median. Dotted "
        "line: today's value.",
        "Banda scura: dal 25° al 75° percentile; banda chiara: dal 10° al 90°; linea: mediana. "
        "Linea punteggiata: valore di oggi.",
    ),
    "adr.mc_cagr": (
        "Implied annual rates over {horizon} years: bear {p10}, base {p50}, bull {p90}.",
        "Tassi annui impliciti su {horizon} anni: ribassista {p10}, centrale {p50}, rialzista {p90}.",
    ),
    "adr.mc_unavailable": (
        "Monte Carlo projection not available: insufficient joint price history.",
        "Proiezione Monte Carlo non disponibile: storico congiunto dei prezzi insufficiente.",
    ),
    "adr.hist_title": (
        "Historical 12-month outcomes (for comparison)",
        "Esiti storici a 12 mesi (per confronto)",
    ),
    "adr.s8": ("Suitability context", "Contesto di adeguatezza"),
    "adr.s8_caption": (
        "Internal monitoring thresholds applied to measured data. This section supports, and "
        "does not replace, the MiFID II suitability assessment, which remains the "
        "responsibility of the advisor.",
        "Soglie interne di monitoraggio applicate ai dati misurati. Questa sezione supporta, "
        "e non sostituisce, la valutazione di adeguatezza MiFID II, che resta responsabilità "
        "del consulente.",
    ),
    "adr.s9": (
        "Composite score and what-if analysis",
        "Punteggio composito e analisi what-if",
    ),
    "adr.obs_title": ("Observations", "Rilievi"),
    "adr.whatif_title": (
        "What-if analysis on current holdings",
        "Analisi what-if sui titoli attuali",
    ),
    "adr.whatif_caption": (
        "Mechanical recalculations of the same metrics under alternative weights, shown whether or not they improve the metrics; analysis only, not a recommendation to trade.",
        "Ricalcoli meccanici delle stesse metriche con pesi alternativi, mostrati sia che migliorino sia che peggiorino le metriche; solo analisi, non una raccomandazione a operare.",
    ),
    "adr.s10": ("Review considerations", "Punti per la revisione"),
    "adr.s10_caption": (
        "Items to examine with the client in the light of objectives, horizon and the full "
        "suitability assessment. Descriptive, not personalized recommendations.",
        "Punti da esaminare con il cliente alla luce di obiettivi, orizzonte e valutazione di "
        "adeguatezza completa. Descrittivi, non raccomandazioni personalizzate.",
    ),
    "adr.s11": (
        "Methodology, data sources and disclosures",
        "Metodologia, fonti dei dati e avvertenze",
    ),
    "adr.defs_title": ("Definitions", "Definizioni"),
    "adr.def_te": (
        "Tracking error: annualized standard deviation of the daily difference between "
        "portfolio and benchmark returns.",
        "Tracking error: deviazione standard annualizzata della differenza giornaliera tra "
        "rendimenti del portafoglio e del benchmark.",
    ),
    "adr.def_ir": (
        "Information ratio: difference between portfolio and benchmark CAGR divided by the "
        "tracking error.",
        "Information ratio: differenza tra il CAGR del portafoglio e quello del benchmark "
        "divisa per il tracking error.",
    ),
    "adr.def_capture": (
        "Up / down capture: average portfolio return in periods of positive (negative) "
        "benchmark return divided by the average benchmark return in those periods; monthly "
        "data with at least twelve months, otherwise daily.",
        "Up / down capture: rendimento medio del portafoglio nei periodi di rendimento "
        "positivo (negativo) del benchmark diviso per il rendimento medio del benchmark negli "
        "stessi periodi; dati mensili con almeno dodici mesi, altrimenti giornalieri.",
    ),
    "adr.def_hhi": (
        "HHI: sum of squared capital weights; effective number of positions = 1 / HHI.",
        "HHI: somma dei quadrati dei pesi sul capitale; numero effettivo di posizioni = 1 / HHI.",
    ),
    "adr.def_risk": (
        "Risk contribution: weight × covariance of the position with the portfolio, divided "
        "by portfolio variance; contributions sum to 100%.",
        "Contributo al rischio: peso × covarianza della posizione con il portafoglio, diviso "
        "per la varianza del portafoglio; i contributi sommano al 100%.",
    ),
    "adr.def_episodes": (
        "Drawdown episode: from a running peak to the lowest point before the peak is regained; "
        "durations in calendar days.",
        "Episodio di drawdown: da un massimo al punto più basso prima che il massimo venga "
        "recuperato; durate in giorni di calendario.",
    ),
    "adr.def_scenarios": (
        "Historical 12-month outcomes: returns of all overlapping 252-trading-day windows with "
        "today's weights; percentiles of that distribution.",
        "Esiti storici a 12 mesi: rendimenti di tutte le finestre sovrapposte di 252 giorni di "
        "borsa con i pesi di oggi; percentili di quella distribuzione.",
    ),
    "ov.pdf_advisor": ("Portfolio review (PDF)", "Revisione di portafoglio (PDF)"),
    "ov.pdf_client": ("Client report (PDF)", "Report per il cliente (PDF)"),
    "ov.reports_note": (
        "Portfolio review: working document for the advisor, with suitability context and "
        "Monte Carlo methodology. Client report: four pages for the client. The heading is "
        "printed only on the PDFs downloaded now, kept in this browser session and never "
        "saved in the database.",
        "Revisione di portafoglio: documento di lavoro per il consulente, con contesto di "
        "adeguatezza e metodologia Monte Carlo. Report per il cliente: quattro pagine per il "
        "cliente. L'intestazione compare solo sui PDF scaricati ora, resta in questa sessione "
        "del browser e non viene mai salvata nel database.",
    ),
    "rpt.v_impl_driver_soft": (
        "The largest contributor to risk is {ticker}, with {risk} of total risk.",
        "Il primo contributore al rischio è {ticker}, con il {risk} del rischio totale.",
    ),
    "rpt.v_regime_up": (
        "Over the last quarter volatility rose to {recent} against {full} over the full window; recent beta {beta}.",
        "Nell'ultimo trimestre la volatilità è salita al {recent} contro il {full} dell'intera finestra; beta recente {beta}.",
    ),
    "rpt.v_regime_down": (
        "Over the last quarter volatility eased to {recent} against {full} over the full window; recent beta {beta}.",
        "Nell'ultimo trimestre la volatilità è scesa al {recent} contro il {full} dell'intera finestra; beta recente {beta}.",
    ),
    "rpt.v_regime_stable": (
        "Over the last quarter volatility was {recent}, close to {full} over the full window; recent beta {beta}.",
        "Nell'ultimo trimestre la volatilità è stata del {recent}, vicina al {full} dell'intera finestra; beta recente {beta}.",
    ),
    "rpt.ratio_negative": (
        "Both below the risk-free rate: comparison not meaningful",
        "Entrambi sotto il tasso privo di rischio: confronto non significativo",
    ),
    "rpt.r_factor_missing": (
        "Sector data not available",
        "Dati di settore non disponibili",
    ),
    "rep.within": (
        "within the declared profile",
        "entro il profilo dichiarato",
    ),
    "rep.outside": (
        "OUTSIDE the declared profile",
        "FUORI dal profilo dichiarato",
    ),
    "rep.ref": (
        "Ref. {rid}",
        "Rif. {rid}",
    ),
    "inv.k_invested_partial": (
        "Includes current value where the purchase price is missing",
        "Include il valore attuale dove manca il prezzo di carico",
    ),
    "adr.mc_short": (
        "The joint history is shorter than two years: the projection inherits the returns of a single, possibly exceptional, period.",
        "Lo storico congiunto è più corto di due anni: la proiezione eredita i rendimenti di un solo periodo, forse eccezionale.",
    ),
    "adr.sector_risk_title": (
        "Capital weight and risk contribution by sector",
        "Peso sul capitale e contributo al rischio per settore",
    ),
    "adr.h_sector_weight": (
        "Capital weight",
        "Peso sul capitale",
    ),
    "adr.h_sector_risk": (
        "Risk contribution",
        "Contributo al rischio",
    ),
    "adr.contents": (
        "Contents",
        "Indice",
    ),
    "adr.confidential": (
        "Confidential. Working document prepared for the professional advisor; it supports, and does not replace, the advisor's own assessment. Not investment advice, research, an offer or a solicitation.",
        "Riservato. Documento di lavoro predisposto per il consulente professionale; supporta, e non sostituisce, la sua valutazione. Non è consulenza, ricerca, offerta né sollecitazione.",
    ),
    "adr.kf_title": (
        "Key figures",
        "Dati principali",
    ),
    "adr.growth_title": (
        "Growth of 100 versus {benchmark}",
        "Crescita di 100 rispetto al benchmark {benchmark}",
    ),
    "adr.calendar_title": (
        "Calendar-year returns",
        "Rendimenti per anno solare",
    ),
    "adr.h_year": (
        "Year",
        "Anno",
    ),
    "adr.partial": (
        "(partial)",
        "(parziale)",
    ),
    "adr.calendar_caption": (
        "Current weights applied to each year; partial years cover only the part inside the observation window.",
        "Pesi attuali applicati a ogni anno; gli anni parziali coprono solo la parte dentro la finestra di osservazione.",
    ),
    "adr.rolling_title": (
        "Rolling 12-month return",
        "Rendimento mobile a 12 mesi",
    ),
    "adr.rolling_caption": (
        "Return over the preceding 252 trading days at each date: shows how consistently the portfolio and the benchmark have delivered.",
        "Rendimento dei 252 giorni di borsa precedenti a ogni data: mostra con quanta continuità portafoglio e benchmark hanno reso.",
    ),
    "adr.rollvol_title": (
        "Rolling volatility, 63 trading days",
        "Volatilità mobile, 63 giorni di borsa",
    ),
    "adr.rollvol_caption": (
        "Annualized standard deviation over the preceding quarter: identifies changes in the risk regime.",
        "Deviazione standard annualizzata del trimestre precedente: individua i cambi di regime di rischio.",
    ),
    "adr.tail_title": (
        "Tail risk",
        "Rischio di coda",
    ),
    "adr.tail_caption": (
        "Historical estimates on daily data over the window, no distributional assumption; worst windows use overlapping periods of 5, 21 and 63 trading days.",
        "Stime storiche su dati giornalieri della finestra, nessuna ipotesi sulla distribuzione; le finestre peggiori usano periodi sovrapposti di 5, 21 e 63 giorni di borsa.",
    ),
    "adr.tail_var95": (
        "VaR 95%, 1 day",
        "VaR 95%, 1 giorno",
    ),
    "adr.tail_es95": (
        "Expected Shortfall 95%, 1 day",
        "Expected Shortfall 95%, 1 giorno",
    ),
    "adr.tail_var99": (
        "VaR 99%, 1 day",
        "VaR 99%, 1 giorno",
    ),
    "adr.tail_es99": (
        "Expected Shortfall 99%, 1 day",
        "Expected Shortfall 99%, 1 giorno",
    ),
    "adr.tail_worst_day": (
        "Worst day",
        "Giorno peggiore",
    ),
    "adr.tail_worst_week": (
        "Worst 5 trading days",
        "Peggiori 5 giorni di borsa",
    ),
    "adr.tail_worst_month": (
        "Worst 21 trading days",
        "Peggiori 21 giorni di borsa",
    ),
    "adr.tail_worst_quarter": (
        "Worst 63 trading days",
        "Peggiori 63 giorni di borsa",
    ),
    "adr.corr_title": (
        "Correlation of daily returns between holdings",
        "Correlazione dei rendimenti giornalieri tra i titoli",
    ),
    "adr.corr_caption": (
        "Pairwise correlation over the window (largest holdings). Values close to 1 indicate holdings that move together and add little diversification.",
        "Correlazione tra coppie nella finestra (titoli principali). Valori vicini a 1 indicano titoli che si muovono insieme e aggiungono poca diversificazione.",
    ),
    "adr.fund_title": (
        "Fundamental characteristics by holding",
        "Caratteristiche fondamentali per titolo",
    ),
    "adr.fund_caption": (
        "Last twelve months from SEC EDGAR filings or backup sources; n/a where the data is not available. Descriptive, not a valuation opinion.",
        "Ultimi dodici mesi dai depositi SEC EDGAR o da fonti di riserva; n/d dove il dato non è disponibile. Descrittivo, non un giudizio di valutazione.",
    ),
    "rpt.m_pe_short": (
        "P/E",
        "P/E",
    ),
    "adr.h_window": (
        "Window",
        "Finestra",
    ),
    "adr.worst_21": (
        "Worst historical months (21 trading days), current weights",
        "Peggiori mesi storici (21 giorni di borsa), pesi attuali",
    ),
    "adr.worst_63": (
        "Worst historical quarters (63 trading days), current weights",
        "Peggiori trimestri storici (63 giorni di borsa), pesi attuali",
    ),
    "adr.worst_caption": (
        "Non-overlapping windows with the largest losses over the observation window, replayed with today's weights; the amount applies the loss to today's value. Historical, not a forecast.",
        "Finestre non sovrapposte con le perdite maggiori nella finestra di osservazione, rigiocate con i pesi di oggi; l'importo applica la perdita al valore di oggi. Storico, non una previsione.",
    ),
    "adr.fan_title": (
        "Distribution of simulated values",
        "Distribuzione dei valori simulati",
    ),
    "adr.signoff_title": (
        "Review sign-off",
        "Firma della revisione",
    ),
    "adr.signoff_caption": (
        "Sign-off is part of the advisor's own process; the software does not record it.",
        "La firma fa parte del processo del consulente; il software non la registra.",
    ),
    "adr.so_prepared": (
        "Prepared by",
        "Predisposto da",
    ),
    "adr.so_reviewed": (
        "Reviewed by",
        "Rivisto da",
    ),
    "adr.so_client": (
        "Discussed with the client",
        "Discusso con il cliente",
    ),
    "adr.so_date": (
        "Date",
        "Data",
    ),
    "adr.def_tail": (
        "Expected Shortfall: average return on the days beyond the VaR threshold at the same confidence level; worst N-day window: lowest cumulative return over any N consecutive trading days.",
        "Expected Shortfall: rendimento medio nei giorni oltre la soglia del VaR allo stesso livello di confidenza; peggior finestra di N giorni: il rendimento cumulato più basso su N giorni di borsa consecutivi.",
    ),
    "adr.def_rolling": (
        "Rolling measures: computed at each date on the preceding window (252 trading days for returns, 63 for volatility).",
        "Misure mobili: calcolate a ogni data sulla finestra precedente (252 giorni di borsa per i rendimenti, 63 per la volatilità).",
    ),
    "pos.invalid_ticker": (
        "Not a valid ticker: use letters, digits and . - ^ = only (e.g. AAPL, ENI.MI).",
        "Ticker non valido: solo lettere, cifre e . - ^ = (es. AAPL, ENI.MI).",
    ),
    "adv.code_invalid": (
        "Client code: letters, digits, spaces and - _ . / only (up to 60 characters).",
        "Codice cliente: solo lettere, cifre, spazi e - _ . / (fino a 60 caratteri).",
    ),
}
