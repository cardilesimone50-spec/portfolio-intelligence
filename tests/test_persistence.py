import pandas as pd
import pytest

from src.data.store import (
    delete_portfolio,
    list_portfolios,
    load_analyses,
    log_analysis,
    save_portfolio,
)


def test_save_list_delete_portfolio(tmp_path):
    db = tmp_path / "test.db"
    save_portfolio("Simone", {"AAPL": 4000.0, "MSFT": 3000.0}, db_path=db)
    save_portfolio("Test", {"NVDA": 1000.0}, db_path=db)

    portfolios = list_portfolios(db_path=db)
    assert portfolios["Simone"] == {"AAPL": 4000.0, "MSFT": 3000.0}

    save_portfolio("Simone", {"TSLA": 500.0}, db_path=db)  # sovrascrive
    assert list_portfolios(db_path=db)["Simone"] == {"TSLA": 500.0}

    delete_portfolio("Simone", db_path=db)
    assert "Simone" not in list_portfolios(db_path=db)


def test_empty_portfolio_name_raises(tmp_path):
    with pytest.raises(ValueError, match="vuoto"):
        save_portfolio("  ", {"AAPL": 100.0}, db_path=tmp_path / "test.db")


def test_analysis_history_roundtrip(tmp_path):
    db = tmp_path / "test.db"
    assert load_analyses(db_path=db).empty

    log_analysis("Simone", "1y", 10000.0, 0.184, 72, health=61, db_path=db)
    log_analysis("Simone", "1y", 10000.0, 0.19, 70, health=64, db_path=db)

    history = load_analyses(db_path=db)
    assert len(history) == 2
    assert history.iloc[0]["risk_score"] == 70  # più recente prima
    assert history.iloc[0]["health"] == 64
    assert history.iloc[1]["cum_return"] == pytest.approx(0.184)


def test_old_schema_gets_health_column_migration(tmp_path):
    import sqlite3

    db = tmp_path / "legacy.db"
    with sqlite3.connect(db) as conn:
        conn.execute(
            """CREATE TABLE analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL, portfolio TEXT NOT NULL,
                period TEXT NOT NULL, invested REAL NOT NULL,
                cum_return REAL NOT NULL, risk_score INTEGER NOT NULL
            )"""
        )
        conn.execute(
            "INSERT INTO analyses (timestamp, portfolio, period, invested, "
            "cum_return, risk_score) VALUES ('2026-01-01T10:00:00', 'X', '1y', "
            "5000, 0.1, 50)"
        )

    log_analysis("X", "1y", 5000.0, 0.12, 48, health=70, db_path=db)
    history = load_analyses(db_path=db)
    assert len(history) == 2
    assert history.iloc[0]["health"] == 70
    assert pd.isna(history.iloc[1]["health"])  # riga pre-migrazione
