"""Aggiorna il database locale (data/market.db) con i prezzi dei componenti
del Nasdaq-100: scarica tutto al primo avvio, poi solo i giorni mancanti."""

import pandas as pd
import yfinance as yf

from src.data.cache import load_nasdaq100_prices
from src.data.store import DB_PATH, known_tickers, last_date, save_prices
from src.data.yahoo_client import get_nasdaq100_tickers

FULL_PERIOD = "5y"


def _download(tickers: list[str], **kwargs) -> pd.DataFrame:
    data = yf.download(tickers, auto_adjust=True, progress=False, **kwargs)["Close"]
    if isinstance(data, pd.Series):
        data = data.to_frame(name=tickers[0])
    missing = [t for t in tickers if t not in data.columns or data[t].isna().all()]
    if missing:
        print(f"Nessun dato per {len(missing)} ticker, esclusi: {', '.join(missing)}")
        data = data.drop(columns=missing)
    return data


def update_nasdaq100() -> None:
    # migrazione una tantum dal vecchio CSV, se il database è vuoto
    if not known_tickers() and (legacy := load_nasdaq100_prices()) is not None:
        rows = save_prices(legacy)
        print(f"Migrato il CSV esistente nel database ({rows} righe).")

    tickers = get_nasdaq100_tickers()
    known = set(known_tickers())
    new_tickers = [t for t in tickers if t not in known]
    existing = [t for t in tickers if t in known]
    since = last_date()

    if since is None:
        print(f"Database vuoto: scarico {FULL_PERIOD} di storico per {len(tickers)} ticker...")
        save_prices(_download(tickers, period=FULL_PERIOD))
    else:
        if existing:
            print(f"Aggiorno {len(existing)} ticker dal {since.date()}...")
            update = _download(existing, start=since.strftime("%Y-%m-%d"))
            save_prices(update)
        if new_tickers:
            print(f"Nuovi ticker nell'indice, scarico {FULL_PERIOD}: {', '.join(new_tickers)}")
            save_prices(_download(new_tickers, period=FULL_PERIOD))

    final = last_date()
    print(f"Database aggiornato al {final.date()} ({len(known_tickers())} ticker) in {DB_PATH}")


if __name__ == "__main__":
    update_nasdaq100()
