"""Persistenza: prezzi storici (globali) + portafogli e analisi per-consulente.

Backend agnostico via SQLAlchemy: SQLite in locale/test, Postgres in produzione
B2B. Il motore è scelto da `DATABASE_URL` (es. `postgresql+psycopg://user:pw@host/db`);
default `sqlite:///data/market.db`. Portafogli e analisi sono **isolati per
advisor**: ogni consulente vede e tocca solo i propri clienti (multi-tenant).
"""

import json
import os
from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import (
    Column,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    delete,
    inspect,
    select,
    text,
)
from sqlalchemy.dialects.postgresql import insert as _pg_insert
from sqlalchemy.dialects.sqlite import insert as _sqlite_insert
from sqlalchemy.engine import Engine

DB_PATH = Path("data/market.db")

_metadata = MetaData()

prices_table = Table(
    "prices",
    _metadata,
    Column("date", String, primary_key=True),
    Column("ticker", String, primary_key=True),
    Column("close", Float, nullable=False),
)

portfolios_table = Table(
    "portfolios",
    _metadata,
    # (advisor, name) è la chiave: due consulenti possono avere un portafoglio
    # con lo stesso nome senza collidere.
    Column("advisor", String, primary_key=True),
    Column("name", String, primary_key=True),
    Column("positions", Text, nullable=False),
    Column("updated", String, nullable=False),
)

analyses_table = Table(
    "analyses",
    _metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("advisor", String, nullable=False, index=True),
    Column("timestamp", String, nullable=False),
    Column("portfolio", String, nullable=False),
    Column("period", String, nullable=False),
    Column("invested", Float, nullable=False),
    Column("cum_return", Float, nullable=False),
    Column("risk_score", Integer, nullable=False),
    Column("health", Integer),
)

_ENGINES: dict[str, Engine] = {}


def _resolve_url(url: str | None) -> str:
    """URL del database: argomento → DATABASE_URL → SQLite locale di default."""
    if url:
        return url
    env = os.getenv("DATABASE_URL")
    if env:
        return env
    return f"sqlite:///{DB_PATH}"


def _ensure_schema(engine: Engine) -> None:
    _metadata.create_all(engine)
    # migrazione dolce dei DB pre-multitenancy: aggiunge 'advisor' se manca
    inspector = inspect(engine)
    for table_name in ("portfolios", "analyses"):
        columns = {col["name"] for col in inspector.get_columns(table_name)}
        if "advisor" not in columns:
            with engine.begin() as conn:
                conn.execute(
                    text(f"ALTER TABLE {table_name} ADD COLUMN advisor VARCHAR DEFAULT 'legacy'")
                )


def get_engine(url: str | None = None) -> Engine:
    """Engine SQLAlchemy (cache per URL), con schema garantito al primo uso."""
    resolved = _resolve_url(url)
    engine = _ENGINES.get(resolved)
    if engine is None:
        if resolved.startswith("sqlite:///"):
            DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        engine = create_engine(resolved, future=True)
        _ensure_schema(engine)
        _ENGINES[resolved] = engine
    return engine


# ---------------------------------------------------------------- prezzi (globali)


def save_prices(prices: pd.DataFrame, engine: Engine | None = None) -> int:
    """Salva un DataFrame wide (index date, colonne ticker). Upsert per
    (date, ticker). Restituisce il numero di righe scritte."""
    engine = engine or get_engine()
    long = (
        prices.rename_axis("date")
        .reset_index()
        .melt(id_vars="date", var_name="ticker", value_name="close")
        .dropna(subset=["close"])
    )
    long["date"] = pd.to_datetime(long["date"]).dt.strftime("%Y-%m-%d")
    rows = [
        {"date": d, "ticker": t, "close": float(c)}
        for d, t, c in long.itertuples(index=False, name=None)
    ]
    insert = _pg_insert if engine.dialect.name == "postgresql" else _sqlite_insert
    with engine.begin() as conn:
        for start in range(0, len(rows), 5000):
            chunk = rows[start : start + 5000]
            stmt = insert(prices_table).values(chunk)
            stmt = stmt.on_conflict_do_update(
                index_elements=["date", "ticker"], set_={"close": stmt.excluded.close}
            )
            conn.execute(stmt)
    return len(rows)


def load_prices(engine: Engine | None = None) -> pd.DataFrame | None:
    """DataFrame wide (index date, colonne ticker), o None se vuoto."""
    engine = engine or get_engine()
    with engine.connect() as conn:
        long = pd.read_sql_query(select(prices_table), conn)
    if long.empty:
        return None
    wide = long.pivot(index="date", columns="ticker", values="close")
    wide.index = pd.to_datetime(wide.index)
    return wide.sort_index()


def last_date(engine: Engine | None = None) -> pd.Timestamp | None:
    engine = engine or get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            select(prices_table.c.date).order_by(prices_table.c.date.desc())
        ).first()
    return pd.Timestamp(row[0]) if row and row[0] else None


def known_tickers(engine: Engine | None = None) -> list[str]:
    engine = engine or get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            select(prices_table.c.ticker).distinct().order_by(prices_table.c.ticker)
        ).all()
    return [row[0] for row in rows]


# ---------------------------------------------------------------- portafogli (per advisor)


def save_portfolio(
    advisor: str, name: str, positions: dict[str, float], engine: Engine | None = None
) -> None:
    """Salva (o sovrascrive) un portafoglio del consulente: {ticker: importo}."""
    if not name.strip():
        raise ValueError("The portfolio name cannot be empty")
    engine = engine or get_engine()
    with engine.begin() as conn:
        # delete+insert: idempotente e indipendente dal dialetto/vincoli
        conn.execute(
            delete(portfolios_table).where(
                portfolios_table.c.advisor == advisor,
                portfolios_table.c.name == name.strip(),
            )
        )
        conn.execute(
            portfolios_table.insert().values(
                advisor=advisor,
                name=name.strip(),
                positions=json.dumps(positions),
                updated=datetime.now().isoformat(timespec="seconds"),
            )
        )


def list_portfolios(advisor: str, engine: Engine | None = None) -> dict[str, dict[str, float]]:
    """Portafogli salvati del consulente: {nome: {ticker: importo}}."""
    engine = engine or get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            select(portfolios_table.c.name, portfolios_table.c.positions)
            .where(portfolios_table.c.advisor == advisor)
            .order_by(portfolios_table.c.name)
        ).all()
    return {name: json.loads(positions) for name, positions in rows}


def delete_portfolio(advisor: str, name: str, engine: Engine | None = None) -> None:
    engine = engine or get_engine()
    with engine.begin() as conn:
        conn.execute(
            delete(portfolios_table).where(
                portfolios_table.c.advisor == advisor, portfolios_table.c.name == name
            )
        )


# ---------------------------------------------------------------- storico analisi (per advisor)


def log_analysis(
    advisor: str,
    portfolio_name: str,
    period: str,
    invested: float,
    cum_return: float,
    risk_score: int,
    health: int,
    engine: Engine | None = None,
) -> None:
    engine = engine or get_engine()
    with engine.begin() as conn:
        conn.execute(
            analyses_table.insert().values(
                advisor=advisor,
                timestamp=datetime.now().isoformat(timespec="seconds"),
                portfolio=portfolio_name,
                period=period,
                invested=invested,
                cum_return=cum_return,
                risk_score=risk_score,
                health=health,
            )
        )


def load_analyses(advisor: str, limit: int = 30, engine: Engine | None = None) -> pd.DataFrame:
    """Le ultime analisi salvate dal consulente, dalla più recente."""
    engine = engine or get_engine()
    query = (
        select(
            analyses_table.c.timestamp,
            analyses_table.c.portfolio,
            analyses_table.c.period,
            analyses_table.c.invested,
            analyses_table.c.cum_return,
            analyses_table.c.risk_score,
            analyses_table.c.health,
        )
        .where(analyses_table.c.advisor == advisor)
        .order_by(analyses_table.c.id.desc())
        .limit(limit)
    )
    with engine.connect() as conn:
        return pd.read_sql_query(query, conn)
