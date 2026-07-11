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

    log_analysis("Simone", "1y", 10000.0, 0.184, 72, db_path=db)
    log_analysis("Simone", "1y", 10000.0, 0.19, 70, db_path=db)

    history = load_analyses(db_path=db)
    assert len(history) == 2
    assert history.iloc[0]["risk_score"] == 70  # più recente prima
    assert history.iloc[1]["cum_return"] == pytest.approx(0.184)
