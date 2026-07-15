import pandas as pd

from src.data.store import get_engine, known_tickers, last_date, load_prices, save_prices

PRICES = pd.DataFrame(
    {"AAPL": [100.0, 101.0], "MSFT": [200.0, float("nan")]},
    index=pd.to_datetime(["2026-01-02", "2026-01-03"]),
)


def _engine(tmp_path):
    return get_engine(f"sqlite:///{tmp_path / 'test.db'}")


def test_save_and_load_roundtrip(tmp_path):
    engine = _engine(tmp_path)
    written = save_prices(PRICES, engine=engine)
    assert written == 3  # il NaN non viene salvato

    loaded = load_prices(engine=engine)
    assert list(loaded.columns) == ["AAPL", "MSFT"]
    assert loaded.loc[pd.Timestamp("2026-01-02"), "AAPL"] == 100.0
    assert pd.isna(loaded.loc[pd.Timestamp("2026-01-03"), "MSFT"])


def test_load_empty_returns_none(tmp_path):
    assert load_prices(engine=_engine(tmp_path)) is None


def test_upsert_overwrites_same_date(tmp_path):
    engine = _engine(tmp_path)
    save_prices(PRICES, engine=engine)
    updated = pd.DataFrame({"AAPL": [999.0]}, index=pd.to_datetime(["2026-01-03"]))
    save_prices(updated, engine=engine)

    loaded = load_prices(engine=engine)
    assert loaded.loc[pd.Timestamp("2026-01-03"), "AAPL"] == 999.0
    assert len(loaded) == 2  # nessuna riga duplicata


def test_last_date_and_known_tickers(tmp_path):
    engine = _engine(tmp_path)
    assert last_date(engine=engine) is None
    assert known_tickers(engine=engine) == []

    save_prices(PRICES, engine=engine)
    assert last_date(engine=engine) == pd.Timestamp("2026-01-03")
    assert known_tickers(engine=engine) == ["AAPL", "MSFT"]


def test_incremental_merge_adds_new_dates_and_tickers(tmp_path):
    engine = _engine(tmp_path)
    save_prices(PRICES, engine=engine)
    increment = pd.DataFrame(
        {"AAPL": [102.0], "NVDA": [50.0]}, index=pd.to_datetime(["2026-01-04"])
    )
    save_prices(increment, engine=engine)

    loaded = load_prices(engine=engine)
    assert len(loaded) == 3
    assert "NVDA" in loaded.columns
    assert loaded.loc[pd.Timestamp("2026-01-04"), "AAPL"] == 102.0
