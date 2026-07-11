import pandas as pd

from src.data.store import known_tickers, last_date, load_prices, save_prices

PRICES = pd.DataFrame(
    {"AAPL": [100.0, 101.0], "MSFT": [200.0, float("nan")]},
    index=pd.to_datetime(["2026-01-02", "2026-01-03"]),
)


def test_save_and_load_roundtrip(tmp_path):
    db = tmp_path / "test.db"
    written = save_prices(PRICES, db_path=db)
    assert written == 3  # il NaN non viene salvato

    loaded = load_prices(db_path=db)
    assert list(loaded.columns) == ["AAPL", "MSFT"]
    assert loaded.loc[pd.Timestamp("2026-01-02"), "AAPL"] == 100.0
    assert pd.isna(loaded.loc[pd.Timestamp("2026-01-03"), "MSFT"])


def test_load_empty_returns_none(tmp_path):
    assert load_prices(db_path=tmp_path / "missing.db") is None


def test_upsert_overwrites_same_date(tmp_path):
    db = tmp_path / "test.db"
    save_prices(PRICES, db_path=db)
    updated = pd.DataFrame({"AAPL": [999.0]}, index=pd.to_datetime(["2026-01-03"]))
    save_prices(updated, db_path=db)

    loaded = load_prices(db_path=db)
    assert loaded.loc[pd.Timestamp("2026-01-03"), "AAPL"] == 999.0
    assert len(loaded) == 2  # nessuna riga duplicata


def test_last_date_and_known_tickers(tmp_path):
    db = tmp_path / "test.db"
    assert last_date(db_path=db) is None
    assert known_tickers(db_path=db) == []

    save_prices(PRICES, db_path=db)
    assert last_date(db_path=db) == pd.Timestamp("2026-01-03")
    assert known_tickers(db_path=db) == ["AAPL", "MSFT"]


def test_incremental_merge_adds_new_dates_and_tickers(tmp_path):
    db = tmp_path / "test.db"
    save_prices(PRICES, db_path=db)
    increment = pd.DataFrame(
        {"AAPL": [102.0], "NVDA": [50.0]}, index=pd.to_datetime(["2026-01-04"])
    )
    save_prices(increment, db_path=db)

    loaded = load_prices(db_path=db)
    assert len(loaded) == 3
    assert "NVDA" in loaded.columns
    assert loaded.loc[pd.Timestamp("2026-01-04"), "AAPL"] == 102.0
