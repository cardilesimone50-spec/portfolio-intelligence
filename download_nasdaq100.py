"""Aggiorna il database locale (data/market.db) con i prezzi dei componenti
del Nasdaq-100: scarica tutto al primo avvio, poi solo i giorni mancanti.

Aggiorna anche lo storico degli indici di riferimento (S&P 500, FTSE MIB,
STOXX Europe 600 e QQQ, vedi data/benchmarks.py), che l'analisi usa come
riserva quando nessun provider risponde, e la composizione del Nasdaq-100.

Rigenera anche lo snapshot dei fondamentali (data/nasdaq100_fundamentals.csv),
spedito nel deploy come riserva quando Yahoo non risponde (IP cloud bloccati).
"""

from collections.abc import Sequence

import pandas as pd
import yfinance as yf

from portfolio_intelligence.data.benchmarks import BENCHMARK_TICKERS, benchmark_label
from portfolio_intelligence.data.cache import (
    NASDAQ100_FUNDAMENTALS,
    load_nasdaq100_prices,
    save_nasdaq100_fundamentals,
)
from portfolio_intelligence.data.providers import build_default_chain
from portfolio_intelligence.data.sec_edgar import fetch_sec_fundamentals
from portfolio_intelligence.data.store import (
    DB_PATH,
    known_tickers,
    last_date,
    save_benchmark_prices,
    save_constituents,
    save_prices,
)
from portfolio_intelligence.data.yahoo_client import get_nasdaq100_constituents
from portfolio_intelligence.fundamentals.valuation import fetch_fundamentals

FULL_PERIOD = "5y"
# il benchmark del registro che replica il Nasdaq-100: la composizione si salva sotto di lui
NASDAQ100_BENCHMARK = "QQQ"


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

    constituents = get_nasdaq100_constituents()
    tickers = constituents.index.tolist()
    save_constituents(NASDAQ100_BENCHMARK, constituents)
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
    final_label = final.date() if final is not None else "—"
    print(f"Database aggiornato al {final_label} ({len(known_tickers())} ticker) in {DB_PATH}")


def update_benchmarks(tickers: Sequence[str] = BENCHMARK_TICKERS) -> dict[str, int]:
    """Scarica lo storico completo (FULL_PERIOD) degli indici di riferimento e lo salva.

    Un indice alla volta: la catena restituisce il primo provider che serve
    QUALCOSA, quindi con una richiesta unica un indice mancante non verrebbe
    cercato sugli altri provider. Così ognuno ha il proprio fallback e un indice
    non disponibile non blocca gli altri. Restituisce {ticker: righe salvate}.
    """
    chain = build_default_chain()
    saved: dict[str, int] = {}
    for ticker in tickers:
        try:
            data, source = chain.fetch([ticker], FULL_PERIOD)
        except ValueError as exc:
            print(f"Benchmark {benchmark_label(ticker)} ({ticker}) non disponibile: {exc}")
            continue
        if ticker not in data.columns or data[ticker].dropna().empty:
            print(f"Benchmark {benchmark_label(ticker)} ({ticker}): nessun dato da {source}")
            continue
        saved[ticker] = save_benchmark_prices(data[[ticker]])
        print(f"Benchmark {benchmark_label(ticker)} ({ticker}): {saved[ticker]} righe da {source}")
    return saved


def update_market_data() -> None:
    """Database di mercato completo: componenti del Nasdaq-100 e indici di riferimento."""
    update_nasdaq100()
    update_benchmarks()


def update_fundamentals_snapshot(tickers: list[str]) -> None:
    """Snapshot dei fondamentali solo da SEC EDGAR: dati pubblici, ridistribuibili.

    I multipli usano l'ultima chiusura del database prezzi. I ticker non coperti
    dalla SEC (bilanci IFRS o in altre valute) restano fuori: in app li copre
    la fonte live di riserva, non un file spedito col deploy.
    """
    prices = load_nasdaq100_prices()
    last = prices.ffill().iloc[-1] if prices is not None else pd.Series(dtype=float)
    sec_prices = {t: float(last[t]) for t in tickers if t in last.index and last[t] == last[t]}
    fundamentals = fetch_fundamentals(
        tickers, primary=lambda tks: fetch_sec_fundamentals(tks, sec_prices), use_yahoo=False
    )
    save_nasdaq100_fundamentals(fundamentals.sort_index())
    missing = sorted(set(tickers) - set(fundamentals.index))
    if missing:
        print(f"Non coperti dalla SEC ({len(missing)}): {', '.join(missing)}")
    print(f"Snapshot fondamentali: {len(fundamentals)} ticker in {NASDAQ100_FUNDAMENTALS}")


if __name__ == "__main__":
    update_market_data()
    legacy = load_nasdaq100_prices()
    universe = known_tickers() or (sorted(legacy.columns) if legacy is not None else [])
    update_fundamentals_snapshot(universe)
