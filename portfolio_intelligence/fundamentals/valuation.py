"""Fondamentali di bilancio e multipli di valutazione."""

import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

from portfolio_intelligence.data.yahoo_client import get_ticker_info
from portfolio_intelligence.logging_config import get_logger

log = get_logger(__name__)

# Campo yfinance -> nome colonna del report
_FIELDS = {
    "shortName": "name",
    "sector": "sector",
    "dividendYield": "dividend_yield",  # in punti percentuali (2.5 = 2.5%)
    "totalRevenue": "revenue",
    "netIncomeToCommon": "net_income",
    "grossMargins": "gross_margin",
    "operatingMargins": "operating_margin",
    "profitMargins": "net_margin",
    "totalDebt": "total_debt",
    "debtToEquity": "debt_to_equity",
    "revenueGrowth": "revenue_growth",
    "earningsGrowth": "earnings_growth",
    "trailingPE": "pe",
    "forwardPE": "forward_pe",
    "enterpriseToEbitda": "ev_ebitda",
    "priceToSalesTrailing12Months": "ps",
}
FUNDAMENTAL_COLUMNS = list(_FIELDS.values())
YAHOO_SOURCE = "Yahoo Finance"

_ATTEMPTS = 2  # Yahoo risponde a singhiozzo (rate limit): un secondo tentativo basta quasi sempre
_RETRY_DELAY = 0.8


def _fetch_info(ticker: str) -> dict | None:
    """`info` di Yahoo con un nuovo tentativo su errore o risposta vuota."""
    for attempt in range(_ATTEMPTS):
        try:
            info = get_ticker_info(ticker)
        except Exception:
            info = None
        if info:
            return info
        if attempt < _ATTEMPTS - 1:
            time.sleep(_RETRY_DELAY)
    return None


def fetch_fundamentals(
    tickers: list[str],
    fallback: pd.DataFrame | None = None,
    primary: Callable[[list[str]], dict[str, dict]] | None = None,
    use_yahoo: bool = True,
) -> pd.DataFrame:
    """Scarica i fondamentali per una lista di ticker, una riga per ticker.

    Ordine delle fonti: `primary` (es. SEC EDGAR, dati pubblici riutilizzabili),
    poi Yahoo per i ticker rimasti (se `use_yahoo`), poi `fallback` (es. lo
    snapshot Nasdaq-100 spedito col deploy). La colonna `source` dice da dove
    arriva ogni riga. I ticker senza dati vengono esclusi; se nessun ticker ha
    dati solleva ValueError. I campi assenti per un singolo ticker restano NaN.
    """
    rows: dict[str, dict] = {}
    if primary is not None:
        try:
            rows.update(primary(tickers))
        except Exception as exc:  # noqa: BLE001 — la fonte primaria non deve bloccare
            log.warning("Primary fundamentals source failed: %s", exc)

    missing = [t for t in tickers if t not in rows]
    if use_yahoo and missing:
        # una richiesta HTTP per ticker: in parallelo il tempo diventa ~costante
        with ThreadPoolExecutor(max_workers=8) as executor:
            for ticker, info in zip(missing, executor.map(_fetch_info, missing), strict=True):
                if not info or info.get("totalRevenue") is None:
                    continue
                rows[ticker] = {column: info.get(field) for field, column in _FIELDS.items()}
                rows[ticker]["source"] = YAHOO_SOURCE

    if fallback is not None:
        for ticker in tickers:
            if ticker not in rows and ticker in fallback.index:
                rows[ticker] = (
                    fallback.loc[ticker].reindex([*FUNDAMENTAL_COLUMNS, "source"]).to_dict()
                )

    if not rows:
        raise ValueError(f"No fundamental data found for: {', '.join(tickers)}")

    return pd.DataFrame.from_dict(rows, orient="index")


def empty_fundamentals(tickers: list[str]) -> pd.DataFrame:
    """Tabella fondamentali tutta NaN: l'analisi prosegue senza bilanci."""
    return pd.DataFrame(index=pd.Index(tickers), columns=FUNDAMENTAL_COLUMNS, dtype=object)


class FundamentalsCache:
    """Cache per ticker dei fondamentali, condivisa tra le sessioni (dati pubblici).

    Una cache sulla tupla intera di ticker riscaricava tutto a ogni combinazione
    nuova (aggiungere un titolo = rifare tutti) e non ricordava i ticker senza
    dati (ETF): l'eccezione non resta in cache, quindi ogni interazione
    ripeteva le richieste. Qui si scaricano solo i ticker mancanti e anche il
    "nessun dato" resta in memoria, per un tempo più breve (`negative_ttl`):
    un'interruzione temporanea della fonte non nasconde i dati per un'ora.
    """

    def __init__(
        self,
        ttl: float = 3600.0,
        negative_ttl: float = 600.0,
        clock: Callable[[], float] = time.monotonic,
        max_entries: int = 2048,
    ):
        self._ttl = ttl
        self._negative_ttl = negative_ttl
        self._max_entries = max_entries
        self._clock = clock
        self._entries: dict[str, tuple[float, dict | None]] = {}
        self._lock = threading.Lock()

    def _fresh(self, ticker: str, now: float) -> tuple[bool, dict | None]:
        entry = self._entries.get(ticker)
        if entry is None:
            return False, None
        stored_at, row = entry
        limit = self._ttl if row is not None else self._negative_ttl
        return (now - stored_at < limit), row

    def get(self, tickers: list[str], fetch: Callable[[list[str]], pd.DataFrame]) -> pd.DataFrame:
        """Righe per `tickers`; `fetch` riceve solo i ticker non in cache.

        Solleva ValueError se nessun ticker ha dati, come `fetch_fundamentals`.
        """
        now = self._clock()
        rows: dict[str, dict | None] = {}
        with self._lock:
            for ticker in tickers:
                hit, row = self._fresh(ticker, now)
                if hit:
                    rows[ticker] = row
        missing = [ticker for ticker in tickers if ticker not in rows]
        if missing:
            try:
                frame = fetch(missing)
            except ValueError:  # nessun dato per nessuno dei mancanti
                frame = pd.DataFrame()
            fetched = {
                ticker: (frame.loc[ticker].to_dict() if ticker in frame.index else None)
                for ticker in missing
            }
            with self._lock:
                stamp = self._clock()
                for ticker, row in fetched.items():
                    self._entries[ticker] = (stamp, row)
                # ticker liberi nella vista Fondamentali: la memoria resta limitata
                overflow = len(self._entries) - self._max_entries
                if overflow > 0:
                    oldest = sorted(self._entries, key=lambda tk: self._entries[tk][0])
                    for ticker in oldest[:overflow]:
                        del self._entries[ticker]
            rows.update(fetched)
        found = {ticker: rows[ticker] for ticker in tickers if rows.get(ticker) is not None}
        if not found:
            raise ValueError(f"No fundamental data found for: {', '.join(tickers)}")
        return pd.DataFrame.from_dict(found, orient="index")

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()
