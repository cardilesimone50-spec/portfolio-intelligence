"""Persistenza: prezzi storici (globali) + portafogli e analisi per-consulente.

Dati di mercato globali: `prices` (componenti del Nasdaq-100, per le viste di
mercato), `benchmark_prices` (storico degli indici di riferimento, separato
così gli indici non finiscono nell'universo dei titoli) e
`benchmark_constituents` (composizione degli universi, per lo stock-picking).

Backend agnostico via SQLAlchemy: SQLite in locale/test, Postgres in produzione
B2B. Il motore è scelto da `DATABASE_URL` (es. `postgresql+psycopg://user:pw@host/db`);
default `sqlite:///data/market.db`. Portafogli e analisi sono **isolati per
advisor**: ogni consulente vede e tocca solo i propri clienti (multi-tenant).

Schema versionato con Alembic (`alembic.ini` + `migrations/`, stessa
risoluzione URL qui sotto). `_ensure_schema` resta un `create_all` idempotente
per SQLite/dev/test (comodo, non richiede di lanciare Alembic); in produzione
su Postgres usare `alembic upgrade head` (DB nuovo) o `alembic stamp head`
(DB già esistente) — vedi README.
"""

import json
import os
import secrets
import threading
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
    update,
)
from sqlalchemy.dialects.postgresql import insert as _pg_insert
from sqlalchemy.dialects.sqlite import insert as _sqlite_insert
from sqlalchemy.engine import Engine, make_url

from portfolio_intelligence.config import DEFAULT_RISK_PROFILE, RISK_PROFILES
from portfolio_intelligence.data.benchmarks import (
    BENCHMARKS,
    DEFAULT_BENCHMARK,
    benchmark_or_default,
    canonical_benchmark,
)
from portfolio_intelligence.data.validators import (
    is_valid_client_code,
    safe_load_positions,
    validate_price_rows,
)

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
    # profilo di rischio dichiarato del cliente (Conservative/Moderate/Aggressive)
    Column("risk_profile", String, nullable=True),
    # benchmark di riferimento del cliente (ticker di data/benchmarks.py); NULL = predefinito
    Column("benchmark", String, nullable=True),
)

# storico degli indici di riferimento, nella valuta di quotazione (come `prices`)
benchmark_prices_table = Table(
    "benchmark_prices",
    _metadata,
    Column("date", String, primary_key=True),
    Column("ticker", String, primary_key=True),
    Column("close", Float, nullable=False),
)

# composizione di un universo di riferimento: base per lo stock-picking futuro
benchmark_constituents_table = Table(
    "benchmark_constituents",
    _metadata,
    Column("benchmark", String, primary_key=True),
    Column("ticker", String, primary_key=True),
    Column("name", String, nullable=True),
    Column("weight", Float, nullable=True),  # peso nell'indice, frazione (0.08 = 8%)
    Column("as_of", String, nullable=False),
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

# traccia chi ha fatto cosa: requisito minimo di audit per un uso B2B
audit_log_table = Table(
    "audit_log",
    _metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("advisor", String, nullable=False, index=True),
    Column("timestamp", String, nullable=False),
    Column("action", String, nullable=False),
    Column("detail", String, nullable=False, default=""),
)

_ENGINES: dict[str, Engine] = {}
# URL su cui lo schema completo (anche le tabelle per advisor) è già garantito
_TENANT_SCHEMA_READY: set[str] = set()
# (URL, tabella) dei dati di mercato già garantiti (download di prezzi e indici)
_MARKET_TABLES_READY: set[tuple[str, str]] = set()
# le sessioni Streamlit sono thread: creazione dell'engine e DDL una volta sola
_ENGINE_LOCK = threading.RLock()


def _resolve_url(url: str | None) -> str:
    """URL del database: argomento → DATABASE_URL → SQLite locale di default."""
    if url:
        return url
    env = os.getenv("DATABASE_URL")
    if env:
        return env
    return f"sqlite:///{DB_PATH}"


def sqlite_file(url: str | None = None) -> Path | None:
    """Il file del database se l'URL è SQLite su file, altrimenti None (es. Postgres).

    L'URL è interpretato da SQLAlchemy: parametri come `?timeout=30` e driver
    espliciti (`sqlite+pysqlite:///`) non finiscono nel percorso.
    """
    parsed = make_url(_resolve_url(url))
    if parsed.get_backend_name() != "sqlite" or parsed.query.get("uri"):
        return None
    database = parsed.database
    return None if database in (None, "", ":memory:") else Path(database)


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
    # stessa migrazione dolce per profilo di rischio e benchmark per cliente
    portfolio_columns = {col["name"] for col in inspector.get_columns("portfolios")}
    for column in ("risk_profile", "benchmark"):
        if column not in portfolio_columns:
            with engine.begin() as conn:
                conn.execute(text(f"ALTER TABLE portfolios ADD COLUMN {column} VARCHAR"))


def _engine_for(resolved: str) -> Engine:
    """Engine in cache per URL, senza toccare lo schema (né creare il file SQLite).

    Pooling esplicito solo per Postgres (produzione, più connessioni
    concorrenti): `pool_pre_ping` evita errori su connessioni scadute dal lato
    server, `pool_size`/`max_overflow` limitano le connessioni aperte per
    istanza. SQLite resta sui default di SQLAlchemy (single-writer, il
    pooling non aiuta).
    """
    with _ENGINE_LOCK:
        engine = _ENGINES.get(resolved)
        if engine is None:
            if resolved.startswith("sqlite:///"):
                engine = create_engine(resolved, future=True)
            else:
                engine = create_engine(
                    resolved,
                    future=True,
                    pool_pre_ping=True,
                    pool_size=5,
                    max_overflow=10,
                )
            _ENGINES[resolved] = engine
        return engine


def _prepare_sqlite_dir(resolved: str) -> None:
    path = sqlite_file(resolved)
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)


def get_engine(url: str | None = None) -> Engine:
    """Engine con lo schema completo (prezzi e tabelle per advisor) garantito al primo uso.

    Solo per l'area Advisor e la persistenza per consulente. I dati di mercato
    passano da `market_engine`, che non crea le tabelle dei consulenti: l'area
    Investor legge i prezzi senza toccare portafogli, analisi o audit log.
    """
    resolved = _resolve_url(url)
    _prepare_sqlite_dir(resolved)
    engine = _engine_for(resolved)
    with _ENGINE_LOCK:
        if resolved not in _TENANT_SCHEMA_READY:
            _ensure_schema(engine)
            _TENANT_SCHEMA_READY.add(resolved)
    return engine


def market_engine(url: str | None = None) -> Engine:
    """Engine per i soli prezzi di mercato: nessuna tabella per advisor, nessuno schema."""
    return _engine_for(_resolve_url(url))


def _has_table(engine: Engine, table: Table) -> bool:
    """True se la tabella esiste; un SQLite su file assente non viene creato."""
    url = engine.url
    database = url.database if url.get_backend_name() == "sqlite" else None
    if database not in (None, "", ":memory:") and not Path(str(database)).exists():
        return False
    return inspect(engine).has_table(table.name)


def _has_prices(engine: Engine) -> bool:
    return _has_table(engine, prices_table)


def _market_writer(table: Table, engine: Engine | None) -> Engine:
    """Engine per scrivere un dato di mercato: crea solo `table`, mai le tabelle per advisor.

    Sotto lo stesso lock dello schema: due prime scritture non la creano due volte.
    """
    if engine is None:
        resolved = _resolve_url(None)
        _prepare_sqlite_dir(resolved)
        engine = _engine_for(resolved)
    key = engine.url.render_as_string(hide_password=False)
    with _ENGINE_LOCK:
        if (key, table.name) not in _MARKET_TABLES_READY and key not in _TENANT_SCHEMA_READY:
            table.create(engine, checkfirst=True)
            _MARKET_TABLES_READY.add((key, table.name))
    return engine


# ---------------------------------------------------------------- prezzi (globali)


def save_prices(prices: pd.DataFrame, engine: Engine | None = None) -> int:
    """Salva un DataFrame wide (index date, colonne ticker). Upsert per
    (date, ticker). Restituisce il numero di righe scritte."""
    # solo la tabella prezzi: scaricare i dati di mercato non crea quelle per advisor
    engine = _market_writer(prices_table, engine)
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
    """DataFrame wide (index date, colonne ticker), o None se vuoto.

    Le righe non valide (data/prezzo corrotti) vengono scartate con un
    warning in log invece di far crashare il pivot — vedi `validate_price_rows`.
    """
    engine = engine or market_engine()
    if not _has_prices(engine):
        return None
    with engine.connect() as conn:
        long = pd.read_sql_query(select(prices_table), conn)
    long = validate_price_rows(long)
    if long.empty:
        return None
    wide = long.pivot(index="date", columns="ticker", values="close")
    wide.index = pd.to_datetime(wide.index)
    return wide.sort_index()


def last_date(engine: Engine | None = None) -> pd.Timestamp | None:
    engine = engine or market_engine()
    if not _has_prices(engine):
        return None
    with engine.connect() as conn:
        row = conn.execute(
            select(prices_table.c.date).order_by(prices_table.c.date.desc())
        ).first()
    return pd.Timestamp(row[0]) if row and row[0] else None


def known_tickers(engine: Engine | None = None) -> list[str]:
    engine = engine or market_engine()
    if not _has_prices(engine):
        return []
    with engine.connect() as conn:
        rows = conn.execute(
            select(prices_table.c.ticker).distinct().order_by(prices_table.c.ticker)
        ).all()
    return [row[0] for row in rows]


# ---------------------------------------------------------------- benchmark (globali)


def save_benchmark_prices(prices: pd.DataFrame, engine: Engine | None = None) -> int:
    """Sostituisce lo storico salvato di ogni benchmark presente in `prices`.

    `prices` è wide (index date, colonne ticker). Sostituzione, non upsert: le
    chiusure rettificate di un ETF cambiano all'indietro a ogni stacco di
    dividendo, quindi lo storico di un benchmark viene sempre da un solo
    download coerente. Restituisce il numero di righe scritte. Come `save_prices`,
    crea solo la propria tabella.
    """
    engine = _market_writer(benchmark_prices_table, engine)
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
    tickers = sorted({row["ticker"] for row in rows})
    with engine.begin() as conn:
        conn.execute(
            delete(benchmark_prices_table).where(benchmark_prices_table.c.ticker.in_(tickers))
        )
        for start in range(0, len(rows), 5000):
            conn.execute(benchmark_prices_table.insert().values(rows[start : start + 5000]))
    return len(rows)


def load_benchmark_prices(
    ticker: str, start: str | None = None, engine: Engine | None = None
) -> pd.Series | None:
    """Storico salvato di un benchmark (dalla data ISO `start`, se data), o None se assente.

    Lettura dal `market_engine`: anche dall'area Investor non crea file né tabelle.
    """
    engine = engine or market_engine()
    if not _has_table(engine, benchmark_prices_table):
        return None
    query = select(benchmark_prices_table).where(benchmark_prices_table.c.ticker == ticker)
    if start:
        query = query.where(benchmark_prices_table.c.date >= start)
    with engine.connect() as conn:
        long = pd.read_sql_query(query, conn)
    long = validate_price_rows(long)
    if long.empty:
        return None
    return pd.Series(
        long["close"].to_numpy(), index=pd.DatetimeIndex(long["date"]), name=ticker
    ).sort_index()


def save_constituents(
    benchmark: str,
    constituents: pd.DataFrame,
    as_of: str | None = None,
    engine: Engine | None = None,
) -> int:
    """Sostituisce la composizione salvata di un universo di riferimento.

    `constituents` ha i ticker come indice e, facoltative, le colonne `name`
    e `weight` (frazione). `as_of` è la data ISO della composizione (default
    oggi). Restituisce il numero di componenti salvati.
    """
    if benchmark not in BENCHMARKS:
        raise ValueError(f"Unknown benchmark: {benchmark}")
    engine = _market_writer(benchmark_constituents_table, engine)
    as_of = as_of or datetime.now().date().isoformat()
    frame = constituents[~constituents.index.duplicated(keep="first")]

    def cell(column: str, ticker: str) -> object:
        if column not in frame.columns or pd.isna(frame.at[ticker, column]):
            return None
        value = frame.at[ticker, column]
        return float(value) if column == "weight" else str(value)

    rows = [
        {
            "benchmark": benchmark,
            "ticker": str(ticker),
            "name": cell("name", ticker),
            "weight": cell("weight", ticker),
            "as_of": as_of,
        }
        for ticker in frame.index
    ]
    with engine.begin() as conn:
        conn.execute(
            delete(benchmark_constituents_table).where(
                benchmark_constituents_table.c.benchmark == benchmark
            )
        )
        if rows:
            conn.execute(benchmark_constituents_table.insert().values(rows))
    return len(rows)


def load_constituents(benchmark: str, engine: Engine | None = None) -> pd.DataFrame:
    """Composizione salvata (index ticker; colonne name, weight, as_of), vuota se assente."""
    engine = engine or market_engine()
    columns = ["name", "weight", "as_of"]
    if not _has_table(engine, benchmark_constituents_table):
        return pd.DataFrame(columns=columns, index=pd.Index([], name="ticker"))
    query = (
        select(
            benchmark_constituents_table.c.ticker,
            benchmark_constituents_table.c.name,
            benchmark_constituents_table.c.weight,
            benchmark_constituents_table.c.as_of,
        )
        .where(benchmark_constituents_table.c.benchmark == benchmark)
        .order_by(benchmark_constituents_table.c.ticker)
    )
    with engine.connect() as conn:
        return pd.read_sql_query(query, conn).set_index("ticker")


# ---------------------------------------------------------------- portafogli (per advisor)


def _registered_benchmark(benchmark: str) -> str:
    """Il ticker del registro da salvare: i ticker storici passano alla serie total return."""
    canonical = canonical_benchmark(benchmark)
    if canonical is None:
        raise ValueError(f"Unknown benchmark: {benchmark}")
    return canonical


def save_portfolio(
    advisor: str,
    name: str,
    positions: dict,
    engine: Engine | None = None,
    risk_profile: str | None = None,
    benchmark: str | None = None,
) -> None:
    """Salva (o sovrascrive) un portafoglio del consulente.

    `positions` è {ticker: {"qty": q, "price": p}} (formato con prezzo di
    carico) oppure il legacy {ticker: importo}: il JSON li conserva entrambi.
    `risk_profile` e `benchmark` None mantengono i valori già salvati per quel cliente.
    """
    if not name.strip():
        raise ValueError("The portfolio name cannot be empty")
    if risk_profile is not None and risk_profile not in RISK_PROFILES:
        raise ValueError(f"Unknown risk profile: {risk_profile}")
    if benchmark is not None:
        benchmark = _registered_benchmark(benchmark)
    engine = engine or get_engine()
    where = (portfolios_table.c.advisor == advisor, portfolios_table.c.name == name.strip())
    with engine.begin() as conn:
        saved = conn.execute(
            select(portfolios_table.c.risk_profile, portfolios_table.c.benchmark).where(*where)
        ).first()
        if risk_profile is None and saved is not None:
            risk_profile = saved.risk_profile
        if benchmark is None and saved is not None:
            benchmark = saved.benchmark
        # delete+insert: idempotente e indipendente dal dialetto/vincoli
        conn.execute(delete(portfolios_table).where(*where))
        conn.execute(
            portfolios_table.insert().values(
                advisor=advisor,
                name=name.strip(),
                positions=json.dumps(positions),
                updated=datetime.now().isoformat(timespec="seconds"),
                risk_profile=risk_profile,
                benchmark=benchmark,
            )
        )


class ClientExistsError(ValueError):
    """Esiste già un cliente con questo codice per lo stesso consulente."""


def create_client(
    advisor: str,
    name: str,
    positions: dict,
    risk_profile: str = DEFAULT_RISK_PROFILE,
    engine: Engine | None = None,
    benchmark: str = DEFAULT_BENCHMARK,
) -> None:
    """Crea un cliente nuovo; a differenza di `save_portfolio` non sovrascrive mai.

    Il controllo sta qui, non solo nella UI: un doppio clic o due schede aperte
    non devono poter rimpiazzare un cliente esistente.
    """
    code = name.strip()
    if not code:
        raise ValueError("The client code cannot be empty")
    if not is_valid_client_code(code):
        raise ValueError("Client code: letters, digits, spaces and - _ . / only")
    if risk_profile not in RISK_PROFILES:
        raise ValueError(f"Unknown risk profile: {risk_profile}")
    benchmark = _registered_benchmark(benchmark)
    engine = engine or get_engine()
    with engine.begin() as conn:
        exists = conn.execute(
            select(portfolios_table.c.name).where(
                portfolios_table.c.advisor == advisor, portfolios_table.c.name == code
            )
        ).first()
        if exists:
            raise ClientExistsError(code)
        conn.execute(
            portfolios_table.insert().values(
                advisor=advisor,
                name=code,
                positions=json.dumps(positions),
                updated=datetime.now().isoformat(timespec="seconds"),
                risk_profile=risk_profile,
                benchmark=benchmark,
            )
        )


def _profile_or_default(value: str | None) -> str:
    """Profilo salvato, o "Not set" per i record storici (NULL) e i valori non validi."""
    return value if value in RISK_PROFILES else DEFAULT_RISK_PROFILE


def list_clients(advisor: str, engine: Engine | None = None) -> dict[str, dict]:
    """Il book del consulente: {nome: {"positions", "risk_profile", "benchmark", "updated"}}.

    Stessa tolleranza di `list_portfolios` verso JSON corrotti; i clienti
    salvati prima della scelta del benchmark ricevono quello predefinito.
    """
    engine = engine or get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            select(
                portfolios_table.c.name,
                portfolios_table.c.positions,
                portfolios_table.c.risk_profile,
                portfolios_table.c.benchmark,
                portfolios_table.c.updated,
            )
            .where(portfolios_table.c.advisor == advisor)
            .order_by(portfolios_table.c.name)
        ).all()
    clients = {}
    for name, positions, profile, benchmark, updated in rows:
        parsed = safe_load_positions(advisor, name, positions)
        if parsed is not None:
            clients[name] = {
                "positions": parsed,
                "risk_profile": _profile_or_default(profile),
                "benchmark": benchmark_or_default(benchmark),
                "updated": updated,
            }
    return clients


def list_portfolios(advisor: str, engine: Engine | None = None) -> dict[str, dict]:
    """Portafogli salvati del consulente: {nome: {ticker: posizione}} (nuovo o legacy).

    Un portafoglio con JSON corrotto viene scartato (con warning in log)
    invece di far fallire l'intero book — vedi `safe_load_positions`.
    """
    engine = engine or get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            select(portfolios_table.c.name, portfolios_table.c.positions)
            .where(portfolios_table.c.advisor == advisor)
            .order_by(portfolios_table.c.name)
        ).all()
    result = {}
    for name, positions in rows:
        parsed = safe_load_positions(advisor, name, positions)
        if parsed is not None:
            result[name] = parsed
    return result


REDACTED = "[deleted]"


def delete_portfolio(advisor: str, name: str, engine: Engine | None = None) -> None:
    """Cancellazione (art. 17 GDPR) di un portafoglio cliente: composizione,
    storico delle analisi e nome del cliente nell'audit log (gli eventi restano,
    senza il dato personale)."""
    engine = engine or get_engine()
    with engine.begin() as conn:
        conn.execute(
            delete(portfolios_table).where(
                portfolios_table.c.advisor == advisor, portfolios_table.c.name == name
            )
        )
        conn.execute(
            delete(analyses_table).where(
                analyses_table.c.advisor == advisor, analyses_table.c.portfolio == name
            )
        )
        conn.execute(
            update(audit_log_table)
            .where(audit_log_table.c.advisor == advisor, audit_log_table.c.detail == name)
            .values(detail=REDACTED)
        )


def delete_advisor_data(advisor: str, engine: Engine | None = None) -> dict[str, int]:
    """Cancella tutti i dati di un consulente (richiesta di cancellazione account).

    Portafogli e analisi vengono eliminati. Le righe di audit restano per
    finalità di sicurezza ma senza identità: l'email diventa un codice
    casuale non derivato da essa e il dettaglio (nomi dei clienti) viene oscurato.
    """
    engine = engine or get_engine()
    # codice casuale, non derivabile dall'email: un hash dell'email si potrebbe
    # ricalcolare e ricollegare alla persona (GDPR, considerando 26)
    pseudonym = "deleted:" + secrets.token_hex(8)
    with engine.begin() as conn:
        portfolios = conn.execute(
            delete(portfolios_table).where(portfolios_table.c.advisor == advisor)
        ).rowcount
        analyses = conn.execute(
            delete(analyses_table).where(analyses_table.c.advisor == advisor)
        ).rowcount
        audit = conn.execute(
            update(audit_log_table)
            .where(audit_log_table.c.advisor == advisor)
            .values(advisor=pseudonym, detail=REDACTED)
        ).rowcount
    return {"portfolios": portfolios, "analyses": analyses, "audit_pseudonymized": audit}


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


# ---------------------------------------------------------------- audit (admin, cross-tenant)


def log_audit(advisor: str, action: str, detail: str = "", engine: Engine | None = None) -> None:
    """Registra un evento di audit: chi (`advisor`), cosa (`action`), su cosa (`detail`)."""
    engine = engine or get_engine()
    with engine.begin() as conn:
        conn.execute(
            audit_log_table.insert().values(
                advisor=advisor,
                timestamp=datetime.now().isoformat(timespec="seconds"),
                action=action,
                detail=detail,
            )
        )


def recent_audit(limit: int = 50, engine: Engine | None = None) -> pd.DataFrame:
    """Gli ultimi eventi di audit su tutti i tenant (vista admin, non filtrata per advisor)."""
    engine = engine or get_engine()
    query = (
        select(
            audit_log_table.c.timestamp,
            audit_log_table.c.advisor,
            audit_log_table.c.action,
            audit_log_table.c.detail,
        )
        .order_by(audit_log_table.c.id.desc())
        .limit(limit)
    )
    with engine.connect() as conn:
        return pd.read_sql_query(query, conn)


def platform_stats(engine: Engine | None = None) -> dict:
    """Numeri aggregati cross-tenant per la vista admin: nessun dato di portafoglio,
    solo conteggi (l'isolamento dei dati clienti resta intatto)."""
    engine = engine or get_engine()
    with engine.connect() as conn:
        n_advisors = len(conn.execute(select(portfolios_table.c.advisor).distinct()).all())
        n_portfolios = len(conn.execute(select(portfolios_table.c.name)).all())
        n_analyses = len(conn.execute(select(analyses_table.c.id)).all())
        last_price_date = conn.execute(
            select(prices_table.c.date).order_by(prices_table.c.date.desc())
        ).first()
    return {
        "advisors": n_advisors,
        "portfolios": n_portfolios,
        "analyses": n_analyses,
        "last_price_date": last_price_date[0] if last_price_date else None,
    }
