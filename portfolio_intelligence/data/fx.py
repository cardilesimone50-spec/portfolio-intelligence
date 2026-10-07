"""Conversione valutaria: porta i prezzi USD in EUR per misurare il rischio
che un investitore europeo corre davvero (mercato + cambio).

Limiti dichiarati (MVP): la valuta è dedotta dal suffisso del ticker.
Senza suffisso o con suffisso USA = USD; suffissi dell'eurozona = già EUR;
altri mercati (es. .L Londra, .SW Zurigo) restano non convertiti. Gli indici
di riferimento fanno eccezione: la loro valuta è nel registro `benchmarks.py`
(^STOXX non ha suffisso ma quota in EUR).
"""

import io

import pandas as pd
import requests
import yfinance as yf

from portfolio_intelligence.data.benchmarks import BENCHMARKS
from portfolio_intelligence.data.providers import _start_date
from portfolio_intelligence.logging_config import get_logger

log = get_logger(__name__)

EURUSD_TICKER = "EURUSD=X"  # dollari per 1 euro
# Cambi di riferimento ufficiali BCE (dollari per 1 euro, giorni TARGET):
# gratuiti e riutilizzabili anche commercialmente citando la fonte.
ECB_EURUSD_URL = "https://data-api.ecb.europa.eu/service/data/EXR/D.USD.EUR.SP00.A"

_EUR_SUFFIXES = (".MI", ".PA", ".DE", ".AS", ".BR", ".MC", ".F", ".VI", ".LS", ".HE", ".IR")


def is_usd_listing(ticker: str) -> bool:
    """True se il ticker quota in USD (nessun suffisso o suffisso USA)."""
    ticker = ticker.upper()
    benchmark = BENCHMARKS.get(ticker)
    if benchmark is not None:
        return benchmark.currency == "USD"
    if "." not in ticker:
        return True
    return not ticker.endswith(_EUR_SUFFIXES)


def fetch_eurusd_ecb(period: str = "1y") -> pd.Series:
    """Serie EUR/USD dai cambi di riferimento della Banca Centrale Europea."""
    resp = requests.get(
        ECB_EURUSD_URL,
        params={"startPeriod": _start_date(period).isoformat(), "format": "csvdata"},
        timeout=15,
    )
    resp.raise_for_status()
    frame = pd.read_csv(io.StringIO(resp.text), usecols=["TIME_PERIOD", "OBS_VALUE"])
    series = pd.Series(
        pd.to_numeric(frame["OBS_VALUE"], errors="coerce").to_numpy(),
        index=pd.to_datetime(frame["TIME_PERIOD"]),
        name=EURUSD_TICKER,
    ).dropna()
    if series.empty:
        raise ValueError("ECB: no EUR/USD observations")
    return series.sort_index()


def fetch_eurusd(period: str = "1y") -> pd.Series:
    """Serie storica EURUSD (dollari per 1 euro).

    Primario: cambi di riferimento BCE (fonte ufficiale, riutilizzabile).
    Riserve: endpoint Yahoo chart via HTTP, poi la libreria yfinance.
    """
    try:
        return fetch_eurusd_ecb(period)
    except Exception as exc:  # noqa: BLE001 — qualsiasi problema: si prova la riserva
        log.warning("ECB EUR/USD unavailable, falling back to Yahoo: %s", exc)

    try:
        from portfolio_intelligence.data.providers import YahooChartProvider

        series = YahooChartProvider().fetch([EURUSD_TICKER], period)[EURUSD_TICKER].dropna()
        if not series.empty:
            return series
    except Exception:  # noqa: BLE001 — si prova l'ultima riserva
        pass

    try:
        data = yf.download(EURUSD_TICKER, period=period, auto_adjust=True, progress=False)["Close"]
    except requests.exceptions.RequestException as exc:
        raise ValueError(f"Network error while downloading the EUR/USD rate: {exc}") from exc
    if isinstance(data, pd.DataFrame):
        data = data.iloc[:, 0]
    data = data.dropna()
    if data.empty:
        raise ValueError("No data available for the EUR/USD rate")
    return data


def convert_to_eur(prices: pd.DataFrame, eurusd: pd.Series) -> pd.DataFrame:
    """Converte in EUR le colonne quotate in USD; le altre restano invariate.

    Il cambio viene allineato per data (forward-fill sui giorni senza quotazione FX).
    """
    fx = eurusd.reindex(prices.index).ffill().bfill()
    converted = prices.copy()
    usd_columns = [c for c in prices.columns if is_usd_listing(str(c))]
    if usd_columns:
        converted[usd_columns] = prices[usd_columns].div(fx, axis=0)
    return converted
