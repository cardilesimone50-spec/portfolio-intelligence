"""Costanti di dominio condivise tra i moduli — una sola fonte di verità.

Chiude il debito tecnico P2-14 (ROADMAP.md): `TRADING_DAYS`, l'euristica di
`min_periods` per le correlazioni rolling e le soglie di scoring/check-up
(Sharpe, Sortino, drawdown, beta, correlazione, concentrazione) vivevano
duplicate in più moduli. Qui ogni valore ha un solo posto; i moduli
importano, non ridefiniscono.
"""

TRADING_DAYS = 252

# orizzonte storico predefinito delle analisi. Advisor: 5 anni, più di un ciclo
# di mercato, così metriche e proiezioni Monte Carlo non ereditano un solo anno
# eccezionale. Investor: 1 anno, check-up rapido.
HISTORY_PERIODS = ("1mo", "6mo", "1y", "2y", "5y")
INVESTOR_HISTORY_PERIOD = "1y"
ADVISOR_HISTORY_PERIOD = "5y"

# ------------------------------------------------------------ profilo di rischio
# Profili dichiarabili per un cliente. "Not set" è il valore sicuro per i record
# storici o non validi: non si assegna mai un profilo che il cliente non ha
# dichiarato (sarebbe un'adeguatezza presunta, non verificata).
RISK_PROFILES = ("Not set", "Conservative", "Moderate", "Aggressive")
DEFAULT_RISK_PROFILE = "Not set"

# --------------------------------------------------------- min_periods rolling
# Finestra minima di osservazioni per le correlazioni: evita correlazioni
# spurie tra titoli con poco storico in comune (portfolio_intelligence/portfolio/risk.py).
MIN_PERIODS_CORRELATION = 40  # default statico quando non si passa una finestra dinamica

# Euristica dinamica (pipeline, vista Clients, vista Correlations): usa metà
# dello storico disponibile, clampata tra un minimo e un massimo ragionevoli.
MIN_PERIODS_FLOOR = 15
MIN_PERIODS_CEIL = 60
MIN_PERIODS_RATIO = 0.5


def rolling_min_periods(n_observations: int) -> int:
    """min_periods per una finestra rolling: metà delle osservazioni
    disponibili, clampata tra MIN_PERIODS_FLOOR e MIN_PERIODS_CEIL."""
    target = int(n_observations * MIN_PERIODS_RATIO)
    return max(MIN_PERIODS_FLOOR, min(MIN_PERIODS_CEIL, target))


# ------------------------------------------------------- soglie di scoring (0-100)
# Bande usate da radar_scores/dna_scores/health_breakdown per mappare una
# metrica continua (es. volatilità annua) in uno score 0-100 via `_scale`.
VOLATILITY_SCALE = (0.10, 0.60)  # 10% annuo = 0 (tranquillo), 60% = 100 (estremo)
DRAWDOWN_SCALE = (0.0, 0.50)  # 0% = 0, -50% di drawdown = 100
CORRELATION_SCALE = (0.0, 1.0)
CURRENCY_USD_SCALE = (0.5, 1.0)  # sotto il 50% USD: score pieno; 100% USD: zero
USD_EXPOSURE_HIGH = 0.7  # executive_summary: soglia per menzionare il rischio cambio

# fondamentali: crescita, qualità, valutazione (dna_scores + stock_scores)
REVENUE_GROWTH_SCALE = (0.0, 0.40)
EARNINGS_GROWTH_SCALE = (0.0, 0.60)
NET_MARGIN_SCALE = (0.0, 0.35)
OPERATING_MARGIN_SCALE = (0.0, 0.45)
DEBT_TO_EQUITY_SCALE = (0.0, 200.0)
PE_SCALE = (10.0, 60.0)
PS_SCALE = (2.0, 20.0)
EV_EBITDA_SCALE = (8.0, 40.0)
STOCK_RISK_SCALE = (0.15, 0.80)  # stock_scores: range più ampio di un portafoglio diversificato

# pesi dell'Overall score per singolo titolo (stock_scores)
STOCK_SCORE_WEIGHTS = {"growth": 0.35, "quality": 0.35, "valuation": 0.20, "risk": 0.10}

# etichetta del DNA di portafoglio (dna_label): soglie sugli score 0-100
DNA_GROWTH_HIGH = 70
DNA_RISK_HIGH = 60
DNA_VALUE_HIGH = 60
DNA_RISK_LOW = 35

# ------------------------------------------------- soglie narrative/alert (interpret, insights, alerts)
# Beta vs benchmark: sotto BETA_LOW il portafoglio è difensivo, sopra
# BETA_HIGH amplifica il benchmark (portfolio_intelligence/analytics/interpret.py + insights.py).
BETA_LOW = 0.85
BETA_HIGH = 1.15

# Correlazione media tra titoli: tre bande, dalla più alla più bassa severità.
CORRELATION_HIGH = 0.75  # "quasi identici" — scatta anche un alert
CORRELATION_ELEVATED = 0.6  # "poco diversificato"
CORRELATION_LOW = 0.3  # "ben diversificato"

# Drawdown: bande distinte per contesto (non sono lo stesso numero riusato,
# ma esplicitate qui invece che sparse come letterali).
DRAWDOWN_INTERPRET_NORMAL = -0.10  # interpret_drawdown: sopra = normale
DRAWDOWN_INTERPRET_CORRECTION = -0.20  # interpret_drawdown: sopra = correzione
DRAWDOWN_INTERPRET_BEAR = -0.35  # interpret_drawdown: sopra = bear market
DRAWDOWN_NARRATIVE_HIGH = -0.25  # executive_summary: nota "drawdown elevato"
DRAWDOWN_NARRATIVE_LOW = -0.10  # executive_summary: nota "drawdown contenuto"
DRAWDOWN_NARRATIVE_MENTION = -0.15  # generate_insights: soglia di menzione
DRAWDOWN_ALERT = -0.30  # alerts.py: scatta un alert immediato

# Sharpe ratio: bande di interpretazione (interpret_sharpe).
SHARPE_NEGATIVE = 0.0
SHARPE_MODEST = 0.5
SHARPE_INLINE = 1.0
SHARPE_GOOD = 2.0

# Sortino vs Sharpe: rapporto che segnala asimmetria upside/downside.
SORTINO_UPSIDE_RATIO = 1.25
SORTINO_DOWNSIDE_RATIO = 0.9

# Volatilità: bande di interpretazione testuale (interpret_volatility).
VOLATILITY_LOW = 0.12
VOLATILITY_MID = 0.22
VOLATILITY_HIGH = 0.35

# Concentrazione: un titolo pesa "troppo" se supera il max tra una soglia
# assoluta e 1.5x la sua quota equipesata (duplicato in alerts.py e insights.py).
CONCENTRATION_MIN_ABS = 0.40
CONCENTRATION_FAIR_SHARE_MULT = 1.5
CONCENTRATION_PROBLEM_WEIGHT = 0.25  # find_problems: peso singolo titolo "troppo alto"
CONCENTRATION_SUGGESTION_SCORE = 60  # generate_suggestions: radar Concentration "alto"

# Rischio/volatilità/correlazione sul radar (scala 0-100): soglia "elevata"
# per problemi/suggerimenti.
RADAR_VOLATILITY_HIGH = 70
RADAR_CORRELATION_HIGH = 60

# DNA "Value" basso: suggerisce di guardare ai multipli (generate_suggestions).
DNA_VALUE_LOW = 30

# Dividend yield: sotto questa soglia (punti percentuali) il portafoglio
# genera poco reddito (find_problems).
DIVIDEND_YIELD_LOW = 1.0

# Movimento di un solo giorno: sopra questa soglia (valore assoluto) scatta
# un alert sull'ultima sessione (alerts.py).
DAILY_MOVE_ALERT = -0.02

# Health Score: bande di colore (verde/ambra/rosso), usate da UI, PDF e book
# clienti — stesso numero ripetuto in 4 punti prima di questa centralizzazione.
HEALTH_SCORE_GOOD = 67
HEALTH_SCORE_FAIR = 34

# ------------------------------------------------- controlli di monitoraggio (Advisor)
# Soglie interne della Panoramica cliente: segnalano cosa rivedere, non sono una
# valutazione di adeguatezza MiFID. Riusano le soglie già usate da insights e
# alert, così Panoramica, problemi e PDF non si contraddicono.
MONITOR_MAX_POSITION = CONCENTRATION_PROBLEM_WEIGHT  # peso del primo titolo
MONITOR_MAX_RISK_SHARE = 0.40  # quota del rischio totale spiegata da un solo titolo
MONITOR_MAX_CORRELATION = CORRELATION_ELEVATED
MONITOR_MAX_USD = USD_EXPOSURE_HIGH
MONITOR_MIN_DRAWDOWN = DRAWDOWN_ALERT
