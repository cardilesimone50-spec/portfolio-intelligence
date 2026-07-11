"""Conversione valutaria: porta i prezzi USD in EUR per misurare il rischio
che un investitore europeo corre davvero (mercato + cambio).

Limiti dichiarati (MVP): la valuta è dedotta dal suffisso del ticker.
Senza suffisso o con suffisso USA = USD; suffissi dell'eurozona = già EUR;
altri mercati (es. .L Londra, .SW Zurigo) restano non convertiti.
"""

import pandas as pd
import requests
import yfinance as yf

EURUSD_TICKER = "EURUSD=X"  # dollari per 1 euro

_EUR_SUFFIXES = (".MI", ".PA", ".DE", ".AS", ".BR", ".MC", ".F", ".VI", ".LS", ".HE", ".IR")


def is_usd_listing(ticker: str) -> bool:
    """True se il ticker quota in USD (nessun suffisso o suffisso USA)."""
    ticker = ticker.upper()
    if "." not in ticker:
        return True
    return not ticker.endswith(_EUR_SUFFIXES)


def fetch_eurusd(period: str = "1y") -> pd.Series:
    """Serie storica EURUSD (dollari per 1 euro) da Yahoo Finance."""
    try:
        data = yf.download(EURUSD_TICKER, period=period, auto_adjust=True, progress=False)[
            "Close"
        ]
    except requests.exceptions.RequestException as exc:
        raise ValueError(f"Errore di rete durante il download del cambio EUR/USD: {exc}") from exc
    if isinstance(data, pd.DataFrame):
        data = data.iloc[:, 0]
    data = data.dropna()
    if data.empty:
        raise ValueError("Nessun dato disponibile per il cambio EUR/USD")
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
