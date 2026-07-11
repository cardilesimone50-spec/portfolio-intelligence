"""Database SQLite dei prezzi storici (tabella long: date, ticker, close).

Sostituisce il CSV: upsert idempotente, aggiornamento incrementale,
una sola fonte di verità in data/market.db.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

DB_PATH = Path("data/market.db")


def _connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS prices (
            date TEXT NOT NULL,
            ticker TEXT NOT NULL,
            close REAL NOT NULL,
            PRIMARY KEY (date, ticker)
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS portfolios (
            name TEXT PRIMARY KEY,
            positions TEXT NOT NULL,
            updated TEXT NOT NULL
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            portfolio TEXT NOT NULL,
            period TEXT NOT NULL,
            invested REAL NOT NULL,
            cum_return REAL NOT NULL,
            risk_score INTEGER NOT NULL
        )"""
    )
    return conn


def save_prices(prices: pd.DataFrame, db_path: Path = DB_PATH) -> int:
    """Salva un DataFrame wide (index date, colonne ticker). Upsert: le date
    già presenti vengono sovrascritte. Restituisce il numero di righe scritte."""
    long = (
        prices.rename_axis("date")
        .reset_index()
        .melt(id_vars="date", var_name="ticker", value_name="close")
        .dropna(subset=["close"])
    )
    long["date"] = pd.to_datetime(long["date"]).dt.strftime("%Y-%m-%d")
    with _connect(db_path) as conn:
        conn.executemany(
            "INSERT OR REPLACE INTO prices (date, ticker, close) VALUES (?, ?, ?)",
            long.itertuples(index=False, name=None),
        )
    return len(long)


def load_prices(db_path: Path = DB_PATH) -> pd.DataFrame | None:
    """Restituisce il DataFrame wide (index date, colonne ticker), o None se vuoto."""
    if not db_path.exists():
        return None
    with _connect(db_path) as conn:
        long = pd.read_sql_query("SELECT date, ticker, close FROM prices", conn)
    if long.empty:
        return None
    wide = long.pivot(index="date", columns="ticker", values="close")
    wide.index = pd.to_datetime(wide.index)
    return wide.sort_index()


def last_date(db_path: Path = DB_PATH) -> pd.Timestamp | None:
    if not db_path.exists():
        return None
    with _connect(db_path) as conn:
        row = conn.execute("SELECT MAX(date) FROM prices").fetchone()
    return pd.Timestamp(row[0]) if row and row[0] else None


def known_tickers(db_path: Path = DB_PATH) -> list[str]:
    if not db_path.exists():
        return []
    with _connect(db_path) as conn:
        rows = conn.execute("SELECT DISTINCT ticker FROM prices ORDER BY ticker").fetchall()
    return [row[0] for row in rows]


# ---------------------------------------------------------------- portafogli salvati


def save_portfolio(name: str, positions: dict[str, float], db_path: Path = DB_PATH) -> None:
    """Salva (o sovrascrive) un portafoglio con nome: {ticker: importo}."""
    if not name.strip():
        raise ValueError("Il nome del portafoglio non può essere vuoto")
    with _connect(db_path) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO portfolios (name, positions, updated) VALUES (?, ?, ?)",
            (name.strip(), json.dumps(positions), datetime.now().isoformat(timespec="seconds")),
        )


def list_portfolios(db_path: Path = DB_PATH) -> dict[str, dict[str, float]]:
    """Tutti i portafogli salvati: {nome: {ticker: importo}}."""
    if not db_path.exists():
        return {}
    with _connect(db_path) as conn:
        rows = conn.execute("SELECT name, positions FROM portfolios ORDER BY name").fetchall()
    return {name: json.loads(positions) for name, positions in rows}


def delete_portfolio(name: str, db_path: Path = DB_PATH) -> None:
    with _connect(db_path) as conn:
        conn.execute("DELETE FROM portfolios WHERE name = ?", (name,))


# ---------------------------------------------------------------- storico analisi


def log_analysis(
    portfolio_name: str,
    period: str,
    invested: float,
    cum_return: float,
    risk_score: int,
    db_path: Path = DB_PATH,
) -> None:
    with _connect(db_path) as conn:
        conn.execute(
            "INSERT INTO analyses (timestamp, portfolio, period, invested, cum_return, "
            "risk_score) VALUES (?, ?, ?, ?, ?, ?)",
            (
                datetime.now().isoformat(timespec="seconds"),
                portfolio_name,
                period,
                invested,
                cum_return,
                risk_score,
            ),
        )


def load_analyses(limit: int = 30, db_path: Path = DB_PATH) -> pd.DataFrame:
    """Le ultime analisi salvate, dalla più recente."""
    if not db_path.exists():
        return pd.DataFrame()
    with _connect(db_path) as conn:
        return pd.read_sql_query(
            "SELECT timestamp, portfolio, period, invested, cum_return, risk_score "
            "FROM analyses ORDER BY id DESC LIMIT ?",
            conn,
            params=(limit,),
        )
