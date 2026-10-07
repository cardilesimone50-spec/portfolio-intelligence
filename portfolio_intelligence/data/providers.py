"""Layer provider dei prezzi: una catena con fallback dietro un'unica interfaccia.

Ordine di preferenza (il primo che risponde vince):
1. EODHD — dati con licenza commerciale, attivo se è presente EODHD_API_KEY.
   È la sorgente pensata per l'uso in produzione/bancario.
2. Yahoo chart (HTTP diretto v8) — gratuito, senza chiave, robusto: usa un
   endpoint diverso dalla libreria yfinance (che il cloud spesso blocca) e ne
   controlliamo header, retry e rotazione degli host.
3. Yahoo Finance (libreria yfinance) — comoda ma spesso bloccata sugli IP cloud.
4. Stooq — CSV pubblico, ultimo fallback.

Ogni provider espone `fetch(tickers, period) -> DataFrame` (colonne = ticker,
indice = date) e alza `ProviderError` se non riesce a servire la richiesta.
La catena prova i provider in ordine e restituisce il primo risultato utile.

I ticker in ingresso e le colonne in uscita sono sempre in simbologia Yahoo;
Stooq ed EODHD ne usano una propria, tradotta da `stooq_symbol`/`eodhd_symbol`
(per gli indici di riferimento, dal registro `benchmarks.py`). Un ticker che un
provider non copre viene saltato, non interrogato con un simbolo inventato.
"""

import io
import os
import time
from datetime import date, timedelta
from typing import Protocol

import pandas as pd
import requests

from portfolio_intelligence.data.benchmarks import BENCHMARKS
from portfolio_intelligence.logging_config import get_logger

log = get_logger(__name__)

_PERIOD_DAYS = {
    "1mo": 31,
    "6mo": 186,
    "1y": 372,
    "2y": 745,
    "5y": 1830,
    "max": 7300,
}
# UA minimale: sorprendentemente il WAF di Yahoo blocca (429) le UA "browser"
# elaborate ma lascia passare questa. Non complicare senza riverificare i 429.
_HEADERS = {"User-Agent": "Mozilla/5.0"}


class ProviderError(Exception):
    """Un provider non è riuscito a servire la richiesta."""


def _start_date(period: str) -> date:
    return date.today() - timedelta(days=_PERIOD_DAYS.get(period, 372))


def stooq_symbol(ticker: str) -> str | None:
    """Simbolo Stooq di un ticker Yahoo: `<ticker>.us` per i titoli USA.

    Gli indici (prefisso ^ in Yahoo) hanno simboli propri: solo quelli del
    registro benchmark sono noti, gli altri non sono coperti (None).
    """
    benchmark = BENCHMARKS.get(ticker)
    if benchmark is not None:
        return benchmark.stooq
    if ticker.startswith("^"):
        return None
    return f"{ticker.lower()}.us"


def eodhd_symbol(ticker: str) -> str | None:
    """Simbolo EODHD di un ticker Yahoo: `<TICKER>.US` per i titoli USA,
    `<CODICE>.INDX` per gli indici del registro benchmark, None per gli altri indici."""
    benchmark = BENCHMARKS.get(ticker)
    if benchmark is not None:
        return benchmark.eodhd
    if ticker.startswith("^"):
        return None
    return f"{ticker.upper()}.US"


class PriceProvider(Protocol):
    name: str

    def fetch(self, tickers: list[str], period: str) -> pd.DataFrame: ...


class YahooProvider:
    """yfinance: pratico, non licenziato per la rivendita."""

    name = "Yahoo Finance"

    def fetch(self, tickers: list[str], period: str) -> pd.DataFrame:
        import yfinance as yf

        try:
            data = yf.download(tickers, period=period, auto_adjust=True, progress=False)["Close"]
        except Exception as exc:  # rete o schema
            raise ProviderError(f"Yahoo: {exc}") from exc
        if isinstance(data, pd.Series):
            data = data.to_frame(name=tickers[0])
        if data.empty or data.isna().all().all():
            raise ProviderError("Yahoo: no data")
        return data


class YahooChartProvider:
    """Yahoo chart v8 via HTTP diretto: gratis, senza chiave, resiliente.

    Non usa la libreria yfinance (crumb/cookie, spesso bloccata dal cloud): fa
    una GET su /v8/finance/chart/<ticker>, ruota query1/query2 e ritenta con
    backoff sui 429/errori di rete. Usa il prezzo adjusted quando disponibile.
    """

    name = "Yahoo (chart)"
    _HOSTS = ["https://query1.finance.yahoo.com", "https://query2.finance.yahoo.com"]

    def __init__(self, retries: int = 3, backoff: float = 0.6):
        self._retries = retries
        self._backoff = backoff

    def _result(self, ticker: str, period: str) -> dict:
        rng = period if period in _PERIOD_DAYS else "1y"
        params = {"range": rng, "interval": "1d"}
        last_error: Exception | None = None
        for attempt in range(self._retries):
            host = self._HOSTS[attempt % len(self._HOSTS)]
            try:
                resp = requests.get(
                    f"{host}/v8/finance/chart/{ticker}",
                    params=params,
                    headers=_HEADERS,
                    timeout=15,
                )
                if resp.status_code == 429:
                    last_error = ProviderError("rate limited (429)")
                    time.sleep(self._backoff * (attempt + 1))
                    continue
                resp.raise_for_status()
                result = (resp.json().get("chart") or {}).get("result")
                if not result:
                    raise ProviderError(f"no result for {ticker}")
                return result[0]
            except (requests.RequestException, ValueError, ProviderError) as exc:
                last_error = exc
                time.sleep(self._backoff * (attempt + 1))
        raise ProviderError(f"Yahoo chart {ticker}: {last_error}")

    def _series(self, ticker: str, period: str) -> pd.Series:
        result = self._result(ticker, period)
        timestamps = result.get("timestamp") or []
        indicators = result.get("indicators") or {}
        adjusted = (indicators.get("adjclose") or [{}])[0].get("adjclose")
        close = (indicators.get("quote") or [{}])[0].get("close")
        values = adjusted or close
        if not timestamps or not values:
            raise ProviderError(f"Yahoo chart: empty series for {ticker}")
        # data nell'ora locale della borsa: in UTC le barre FX (23:00 UTC) e
        # asiatiche cadrebbero sul giorno precedente
        offset = int((result.get("meta") or {}).get("gmtoffset") or 0)
        index = pd.to_datetime([ts + offset for ts in timestamps], unit="s").normalize()
        return pd.Series(values, index=index, name=ticker).dropna()

    def fetch(self, tickers: list[str], period: str) -> pd.DataFrame:
        columns = {}
        for ticker in tickers:
            try:
                series = self._series(ticker, period)
            except ProviderError:
                continue
            if not series.empty:
                columns[ticker] = series
        if not columns:
            raise ProviderError("Yahoo chart: no ticker available")
        return pd.DataFrame(columns).sort_index()


class StooqProvider:
    """Stooq: CSV pubblico gratuito. Simbologia propria, vedi `stooq_symbol`."""

    name = "Stooq"
    _URL = "https://stooq.com/q/d/l/"

    def _fetch_one(self, ticker: str, symbol: str, start: date) -> pd.Series:
        params = {
            "s": symbol,
            "i": "d",
            "d1": start.strftime("%Y%m%d"),
            "d2": date.today().strftime("%Y%m%d"),
        }
        resp = requests.get(self._URL, params=params, headers=_HEADERS, timeout=15)
        resp.raise_for_status()
        frame = pd.read_csv(io.StringIO(resp.text))
        if "Close" not in frame.columns or frame.empty:
            raise ProviderError(f"Stooq: no data for {ticker}")
        series = pd.Series(
            frame["Close"].to_numpy(),
            index=pd.to_datetime(frame["Date"]),
            name=ticker,
        )
        return series

    def fetch(self, tickers: list[str], period: str) -> pd.DataFrame:
        start = _start_date(period)
        columns = {}
        for ticker in tickers:
            symbol = stooq_symbol(ticker)
            if symbol is None:
                continue  # serie non coperta da Stooq
            try:
                columns[ticker] = self._fetch_one(ticker, symbol, start)
            except (requests.RequestException, ProviderError, ValueError):
                continue
        if not columns:
            raise ProviderError("Stooq: no ticker available")
        return pd.DataFrame(columns).sort_index()


class EODHDProvider:
    """EOD Historical Data: dati con licenza commerciale (richiede API key)."""

    name = "EODHD"
    _URL = "https://eodhd.com/api/eod/{symbol}"

    def __init__(self, api_key: str):
        self._api_key = api_key

    def _fetch_one(self, ticker: str, symbol: str, start: date) -> pd.Series:
        resp = requests.get(
            self._URL.format(symbol=symbol),
            params={
                "api_token": self._api_key,
                "fmt": "json",
                "from": start.strftime("%Y-%m-%d"),
                "period": "d",
            },
            headers=_HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        rows = resp.json()
        if not rows:
            raise ProviderError(f"EODHD: no data for {ticker}")
        frame = pd.DataFrame(rows)
        # adjusted_close se disponibile, altrimenti close
        col = "adjusted_close" if "adjusted_close" in frame.columns else "close"
        return pd.Series(
            frame[col].to_numpy(),
            index=pd.to_datetime(frame["date"]),
            name=ticker,
        )

    def fetch(self, tickers: list[str], period: str) -> pd.DataFrame:
        start = _start_date(period)
        columns = {}
        for ticker in tickers:
            symbol = eodhd_symbol(ticker)
            if symbol is None:
                continue  # serie non coperta da EODHD
            try:
                columns[ticker] = self._fetch_one(ticker, symbol, start)
            except (requests.RequestException, ProviderError, ValueError, KeyError):
                continue
        if not columns:
            raise ProviderError("EODHD: no ticker available")
        return pd.DataFrame(columns).sort_index()


class ProviderChain:
    """Prova i provider in ordine; restituisce il primo risultato utile."""

    def __init__(self, providers: list[PriceProvider]):
        if not providers:
            raise ValueError("The chain must have at least one provider")
        self._providers = providers

    @property
    def active_source(self) -> str:
        return self._providers[0].name

    def fetch(self, tickers: list[str], period: str) -> tuple[pd.DataFrame, str]:
        """Prezzi per tutti i ticker: i mancanti si chiedono al provider successivo.

        Un risultato parziale non chiude la catena: un ticker che il primo
        provider non serve può arrivare da uno dei successivi.
        """
        errors = []
        frames: list[pd.DataFrame] = []
        sources: list[str] = []
        missing = list(tickers)
        for provider in self._providers:
            if not missing:
                break
            try:
                data = provider.fetch(missing, period)
            except ProviderError as exc:
                log.warning("%s failed, trying next provider: %s", provider.name, exc)
                errors.append(str(exc))
                continue
            served = [c for c in data.columns if c in missing and data[c].notna().any()]
            if not served:
                log.warning("%s returned an empty result, trying next provider", provider.name)
                errors.append(f"{provider.name}: empty result")
                continue
            frames.append(data[served])
            sources.append(provider.name)
            missing = [tk for tk in missing if tk not in served]
            if missing:
                log.info(
                    "%s lacked %d ticker(s), trying next provider", provider.name, len(missing)
                )
        if not frames:
            log.error(
                "All providers failed for %d ticker(s): %s", len(tickers), " · ".join(errors)
            )
            raise ValueError("No data provider responded: " + " · ".join(errors))
        data = pd.concat(frames, axis=1).sort_index() if len(frames) > 1 else frames[0]
        return data, " + ".join(sources)


def build_default_chain() -> ProviderChain:
    """Catena: EODHD (se c'è la key) → Yahoo chart HTTP → yfinance → Stooq.

    Yahoo chart (HTTP diretto) è primo tra i gratuiti perché è quello che
    regge meglio sugli IP cloud, dove la libreria yfinance viene spesso bloccata.
    """
    providers: list[PriceProvider] = []
    api_key = os.getenv("EODHD_API_KEY")
    if api_key:
        providers.append(EODHDProvider(api_key))
    providers.append(YahooChartProvider())
    providers.append(YahooProvider())
    providers.append(StooqProvider())
    return ProviderChain(providers)
