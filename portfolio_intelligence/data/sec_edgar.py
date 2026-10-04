"""Fondamentali dai bilanci depositati alla SEC (EDGAR, XBRL "companyfacts").

Dati pubblici del governo USA: gratuiti e riutilizzabili anche in un prodotto
commerciale, a differenza di Yahoo. Copertura: le società che depositano
bilanci US-GAAP in dollari (10-K/10-Q); chi deposita in IFRS o in altre valute
(es. molti emittenti esteri con 20-F) non ha qui ricavi in USD e ricade sulle
fonti di riserva.

Calcoli, dichiarati:
- grandezze di flusso (ricavi, utile, margini) sugli ultimi 12 mesi (TTM):
  ultimo esercizio + progressivo dell'anno in corso − stesso progressivo
  dell'anno precedente;
- crescita: ultimo trimestre contro lo stesso trimestre dell'anno prima, o
  esercizio contro esercizio se l'ultimo dato è annuale;
- multipli (P/E, P/S, EV/EBITDA, dividend yield) con prezzo × azioni in
  circolazione; nessuna stima futura, quindi niente P/E prospettico;
- settore dal codice SIC del deposito, ricondotto ai settori usati dall'app.

Policy SEC: massimo 10 richieste al secondo e un User-Agent che dichiari chi
fa le richieste (`SEC_USER_AGENT`, es. "NomeApp contatto@dominio").
"""

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from functools import lru_cache

import requests

from portfolio_intelligence.logging_config import get_logger

log = get_logger(__name__)

SEARCH_URL = "https://efts.sec.gov/LATEST/search-index"
FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
SOURCE = "SEC EDGAR"

REVENUE = [
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "Revenues",
    "SalesRevenueNet",
    "RevenueFromContractWithCustomerIncludingAssessedTax",
    "SalesRevenueGoodsNet",
]
NET_INCOME = ["NetIncomeLoss", "ProfitLoss", "NetIncomeLossAvailableToCommonStockholdersBasic"]
GROSS_PROFIT = ["GrossProfit"]
COST_OF_REVENUE = ["CostOfRevenue", "CostOfGoodsAndServicesSold", "CostOfGoodsSold"]
OPERATING_INCOME = ["OperatingIncomeLoss"]
DEPRECIATION = [
    "DepreciationDepletionAndAmortization",
    "DepreciationAndAmortization",
    "DepreciationAmortizationAndAccretionNet",
]
EQUITY = [
    "StockholdersEquity",
    "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
]
CASH = [
    "CashAndCashEquivalentsAtCarryingValue",
    "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
]
DIVIDENDS_PER_SHARE = [
    "CommonStockDividendsPerShareDeclared",
    "CommonStockDividendsPerShareCashPaid",
]
DIVIDENDS_PAID = ["PaymentsOfDividendsCommonStock", "PaymentsOfDividends"]

_HEADERS_FALLBACK = "Smarteefinance portfolio analysis"


def _headers() -> dict[str, str]:
    return {"User-Agent": os.getenv("SEC_USER_AGENT") or _HEADERS_FALLBACK}


# ------------------------------------------------------------------ settore da SIC

# (da, a, settore): intervalli SIC ricondotti ai settori usati dall'app. Il
# primo intervallo che contiene il codice vince, quindi i casi specifici
# stanno prima di quelli generici.
_SIC_SECTORS: list[tuple[int, int, str]] = [
    (2830, 2836, "Healthcare"),
    (3841, 3851, "Healthcare"),
    (5122, 5122, "Healthcare"),
    (8000, 8099, "Healthcare"),
    (2840, 2844, "Consumer Defensive"),
    (5140, 5149, "Consumer Defensive"),
    (5331, 5331, "Consumer Defensive"),
    (5400, 5499, "Consumer Defensive"),
    (5912, 5912, "Consumer Defensive"),
    (3570, 3579, "Technology"),
    (3660, 3699, "Technology"),
    (7370, 7379, "Technology"),
    (3630, 3639, "Consumer Cyclical"),
    (3711, 3716, "Consumer Cyclical"),
    (3720, 3729, "Industrials"),
    (1311, 1389, "Energy"),
    (2900, 2999, "Energy"),
    (6500, 6553, "Real Estate"),
    (6798, 6798, "Real Estate"),
    (100, 999, "Consumer Defensive"),
    (1000, 1499, "Basic Materials"),
    (1500, 1799, "Industrials"),
    (2000, 2199, "Consumer Defensive"),
    (2200, 2399, "Consumer Cyclical"),
    (2400, 2499, "Basic Materials"),
    (2500, 2599, "Consumer Cyclical"),
    (2600, 2699, "Basic Materials"),
    (2700, 2799, "Communication Services"),
    (2800, 2899, "Basic Materials"),
    (3000, 3399, "Basic Materials"),
    (3400, 3569, "Industrials"),
    (3580, 3599, "Industrials"),
    (3600, 3659, "Technology"),
    (3700, 3799, "Industrials"),
    (3800, 3899, "Technology"),
    (3900, 3999, "Consumer Cyclical"),
    (4000, 4799, "Industrials"),
    (4800, 4899, "Communication Services"),
    (4900, 4999, "Utilities"),
    (5000, 5199, "Industrials"),
    (5200, 5999, "Consumer Cyclical"),
    (6000, 6799, "Financial Services"),
    (7000, 7299, "Consumer Cyclical"),
    (7300, 7399, "Industrials"),
    (7800, 7899, "Communication Services"),
    (7900, 7999, "Consumer Cyclical"),
    (8100, 8999, "Industrials"),
]


def sector_from_sic(sic: str | int | None) -> str | None:
    try:
        code = int(sic) if sic not in (None, "") else None
    except (TypeError, ValueError):
        return None
    if code is None:
        return None
    return next((sector for lo, hi, sector in _SIC_SECTORS if lo <= code <= hi), None)


# ------------------------------------------------------------------ estrazione XBRL


def _facts(company_facts: dict, concept: str, unit: str = "USD") -> list[dict]:
    try:
        return list(company_facts["facts"]["us-gaap"][concept]["units"][unit])
    except KeyError:
        return []


def _span(start: str, end: str) -> int:
    return (date.fromisoformat(end) - date.fromisoformat(start)).days


def _dedupe(facts: list[dict]) -> dict[tuple[str | None, str], float]:
    """(inizio, fine) → valore, tenendo il deposito più recente."""
    out: dict[tuple[str | None, str], float] = {}
    for fact in sorted(facts, key=lambda f: f.get("filed", "")):
        out[(fact.get("start"), fact["end"])] = float(fact["val"])
    return out


def _pick_concept(company_facts: dict, concepts: list[str], unit: str = "USD") -> list[dict]:
    """Il concetto con il dato più recente (le società cambiano tag negli anni)."""
    best: list[dict] = []
    best_end = ""
    for concept in concepts:
        facts = _facts(company_facts, concept, unit)
        if facts:
            end = max(f["end"] for f in facts)
            if end > best_end:
                best, best_end = facts, end
    return best


def _near(a: str, b: date, tolerance: int = 10) -> bool:
    return abs((date.fromisoformat(a) - b).days) <= tolerance


def ttm(facts: list[dict]) -> float | None:
    """Ultimi 12 mesi da fatti di flusso (vedi docstring del modulo)."""
    values = _dedupe([f for f in facts if f.get("start")])
    annual = sorted(
        ((s, e) for (s, e) in values if s and 350 <= _span(s, e) <= 380),
        key=lambda k: k[1],
    )
    if not annual:
        return None
    a_start, a_end = annual[-1]
    fy_start = (date.fromisoformat(a_end) + timedelta(days=1)).isoformat()
    ytd = sorted(
        ((s, e) for (s, e) in values if s and _near(s, date.fromisoformat(fy_start), 3)),
        key=lambda k: k[1],
    )
    total = values[(a_start, a_end)]
    if not ytd:
        return total
    y_start, y_end = ytd[-1]
    if _span(y_start, y_end) >= 350:  # è già un esercizio completo
        return values[(y_start, y_end)]
    prior_end = date.fromisoformat(y_end) - timedelta(days=364)
    prior = [
        (s, e)
        for (s, e) in values
        if s and _near(s, date.fromisoformat(a_start), 3) and _near(e, prior_end, 10)
    ]
    if not prior:
        return total
    return total + values[(y_start, y_end)] - values[prior[0]]


def yoy_growth(facts: list[dict]) -> float | None:
    """Crescita dell'ultimo periodo (trimestre o esercizio) sullo stesso dell'anno prima."""
    values = _dedupe([f for f in facts if f.get("start")])
    # solo trimestri (~90 giorni) ed esercizi (~365): i progressivi semestrali e
    # a nove mesi non sono confrontabili con un singolo periodo
    periods = [
        (s, e, d)
        for (s, e) in values
        if s and (80 <= (d := _span(s, e)) <= 100 or 350 <= d <= 380)
    ]
    if not periods:
        return None
    s, e, d = max(periods, key=lambda p: (p[1], -p[2]))
    target = date.fromisoformat(e) - timedelta(days=364)
    for s0, e0, d0 in periods:
        same_length = abs(d0 - d) <= 10
        if same_length and _near(e0, target, 10):
            previous = values[(s0, e0)]
            if previous > 0:
                return values[(s, e)] / previous - 1
    return None


def latest_instant(facts: list[dict]) -> tuple[str, float] | None:
    values = _dedupe([f for f in facts if not f.get("start")])
    if not values:
        return None
    (_, end), value = max(values.items(), key=lambda kv: kv[0][1])
    return end, value


def shares_outstanding(company_facts: dict) -> float | None:
    """Azioni in circolazione all'ultima data; le classi multiple si sommano.

    Prima la copertina del deposito (dei); alcune società (es. Alphabet) non la
    compilano: allora il totale a bilancio, poi la media diluita del periodo.
    """
    try:
        facts = company_facts["facts"]["dei"]["EntityCommonStockSharesOutstanding"]["units"][
            "shares"
        ]
    except KeyError:
        facts = []
    if not facts:
        balance = latest_instant(_facts(company_facts, "CommonStockSharesOutstanding", "shares"))
        if balance:
            return balance[1]
        diluted = _dedupe(
            _facts(company_facts, "WeightedAverageNumberOfDilutedSharesOutstanding", "shares")
        )
        return max(diluted.items(), key=lambda kv: kv[0][1])[1] if diluted else None
    last_end = max(f["end"] for f in facts)
    latest_filing = max(f.get("filed", "") for f in facts if f["end"] == last_end)
    total = sum(
        float(f["val"])
        for f in facts
        if f["end"] == last_end and f.get("filed", "") == latest_filing
    )
    return total or None


def _debt(company_facts: dict) -> tuple[str, float] | None:
    total = latest_instant(_pick_concept(company_facts, ["LongTermDebt"]))
    noncurrent = latest_instant(_pick_concept(company_facts, ["LongTermDebtNoncurrent"]))
    current = latest_instant(_pick_concept(company_facts, ["LongTermDebtCurrent"]))
    if noncurrent and (not total or noncurrent[0] > total[0]):
        same_date = current and current[0] == noncurrent[0]
        total = (noncurrent[0], noncurrent[1] + (current[1] if same_date and current else 0.0))
    if not total:
        return None
    end, value = total
    for concept in ("CommercialPaper", "ShortTermBorrowings"):
        extra = latest_instant(_facts(company_facts, concept))
        if extra and extra[0] == end:
            value += extra[1]
    return end, value


def display_name(name: str | None) -> str | None:
    """Molti nomi in EDGAR sono tutti maiuscoli ("MICROSOFT CORP"): in tal caso
    si passa a iniziali maiuscole; i nomi già in forma mista restano com'erano."""
    if not name or not name.isupper():
        return name
    return name.title().replace("'S ", "'s ")


def _latest_end(facts: list[dict]) -> str:
    return max((f["end"] for f in facts), default="")


def _depreciation_ttm(company_facts: dict) -> float | None:
    """Ammortamenti TTM: voce unica, oppure materiali + immateriali se più recenti."""
    combined = _pick_concept(company_facts, DEPRECIATION)
    tangible = _facts(company_facts, "Depreciation")
    intangible = _facts(company_facts, "AmortizationOfIntangibleAssets")
    if tangible and _latest_end(tangible) > _latest_end(combined):
        total = ttm(tangible)
        if total is not None and _latest_end(intangible) == _latest_end(tangible):
            total += ttm(intangible) or 0.0
        return total
    return ttm(combined)


def fundamentals_from_facts(
    company_facts: dict, sic: str | int | None, price: float | None
) -> dict | None:
    """Riga di fondamentali con le stesse colonne della fonte Yahoo, o None.

    None se non ci sono ricavi in USD (es. bilanci IFRS): la riga sarebbe vuota.
    """
    revenue_facts = _pick_concept(company_facts, REVENUE)
    revenue = ttm(revenue_facts)
    if not revenue or revenue <= 0:
        return None
    income_facts = _pick_concept(company_facts, NET_INCOME)
    net_income = ttm(income_facts)
    gross = ttm(_pick_concept(company_facts, GROSS_PROFIT))
    if gross is None and (cost := ttm(_pick_concept(company_facts, COST_OF_REVENUE))) is not None:
        gross = revenue - cost
    operating = ttm(_pick_concept(company_facts, OPERATING_INCOME))
    depreciation = _depreciation_ttm(company_facts)
    equity = latest_instant(_pick_concept(company_facts, EQUITY))
    cash = latest_instant(_pick_concept(company_facts, CASH))
    debt = _debt(company_facts)

    def ratio(num: float | None, den: float | None) -> float | None:
        return num / den if num is not None and den else None

    shares = shares_outstanding(company_facts)
    market_cap = price * shares if price and shares else None
    ebitda = operating + depreciation if operating is not None and depreciation else None
    enterprise = (
        market_cap + (debt[1] if debt else 0.0) - (cash[1] if cash else 0.0)
        if market_cap
        else None
    )
    dps = ttm(_pick_concept(company_facts, DIVIDENDS_PER_SHARE, unit="USD/shares"))
    if dps and price:
        dividend_yield: float | None = dps / price * 100
    else:
        paid = ttm(_pick_concept(company_facts, DIVIDENDS_PAID))
        dividend_yield = paid / market_cap * 100 if paid and market_cap else None

    return {
        "name": display_name(company_facts.get("entityName")),
        "sector": sector_from_sic(sic),
        "dividend_yield": dividend_yield,  # punti percentuali, come la fonte Yahoo
        "revenue": revenue,
        "net_income": net_income,
        "gross_margin": ratio(gross, revenue),
        "operating_margin": ratio(operating, revenue),
        "net_margin": ratio(net_income, revenue),
        "total_debt": debt[1] if debt else None,
        "debt_to_equity": (
            debt[1] / equity[1] * 100 if debt and equity and equity[1] > 0 else None
        ),
        "revenue_growth": yoy_growth(revenue_facts),
        "earnings_growth": yoy_growth(income_facts),
        "pe": ratio(market_cap, net_income) if net_income and net_income > 0 else None,
        "forward_pe": None,  # richiede stime degli analisti, non presenti nei bilanci
        "ev_ebitda": ratio(enterprise, ebitda) if ebitda and ebitda > 0 else None,
        "ps": ratio(market_cap, revenue),
    }


# ------------------------------------------------------------------ rete


@lru_cache(maxsize=1024)
def ticker_to_cik(ticker: str) -> int | None:
    """CIK della società dal ticker (BRK.B → BRK-B, come lo scrive la SEC)."""
    symbol = ticker.upper().replace(".", "-")
    resp = requests.get(SEARCH_URL, params={"keysTyped": symbol}, headers=_headers(), timeout=15)
    resp.raise_for_status()
    for hit in resp.json().get("hits", {}).get("hits", []):
        tickers = [t.strip() for t in (hit["_source"].get("tickers") or "").split(",")]
        if symbol in tickers:
            return int(hit["_id"])
    return None


def _get_json(url: str) -> dict:
    resp = requests.get(url, headers=_headers(), timeout=30)
    resp.raise_for_status()
    return resp.json()


def fetch_one(ticker: str, price: float | None = None) -> dict | None:
    cik = ticker_to_cik(ticker)
    if cik is None:
        return None
    facts = _get_json(FACTS_URL.format(cik=cik))
    sic = _get_json(SUBMISSIONS_URL.format(cik=cik)).get("sic")
    row = fundamentals_from_facts(facts, sic, price)
    if row is not None:
        row["source"] = SOURCE
    return row


def fetch_sec_fundamentals(
    tickers: list[str], prices: dict[str, float] | None = None
) -> dict[str, dict]:
    """Righe di fondamentali per i ticker coperti; gli altri restano fuori."""
    prices = prices or {}

    def one(ticker: str) -> tuple[str, dict | None]:
        try:
            return ticker, fetch_one(ticker, prices.get(ticker))
        except (requests.RequestException, ValueError, KeyError) as exc:
            log.warning("SEC EDGAR unavailable for %s: %s", ticker, exc)
            return ticker, None

    # 3 ticker in parallelo × 3 richieste: sotto il limite SEC di 10 al secondo
    with ThreadPoolExecutor(max_workers=3) as executor:
        results = dict(executor.map(one, tickers))
    return {ticker: row for ticker, row in results.items() if row is not None}
