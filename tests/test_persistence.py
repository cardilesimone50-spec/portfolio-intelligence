import pytest

from src.data.store import (
    delete_portfolio,
    get_engine,
    list_portfolios,
    load_analyses,
    log_analysis,
    save_portfolio,
)


def _engine(tmp_path):
    return get_engine(f"sqlite:///{tmp_path / 'test.db'}")


def test_save_list_delete_portfolio(tmp_path):
    engine = _engine(tmp_path)
    save_portfolio("adv@a", "Client Rossi", {"AAPL": 4000.0, "MSFT": 3000.0}, engine=engine)
    save_portfolio("adv@a", "Client Bianchi", {"NVDA": 1000.0}, engine=engine)

    portfolios = list_portfolios("adv@a", engine=engine)
    assert portfolios["Client Rossi"] == {"AAPL": 4000.0, "MSFT": 3000.0}

    save_portfolio("adv@a", "Client Rossi", {"TSLA": 500.0}, engine=engine)  # sovrascrive
    assert list_portfolios("adv@a", engine=engine)["Client Rossi"] == {"TSLA": 500.0}

    delete_portfolio("adv@a", "Client Rossi", engine=engine)
    assert "Client Rossi" not in list_portfolios("adv@a", engine=engine)


def test_portfolios_are_isolated_per_advisor(tmp_path):
    engine = _engine(tmp_path)
    # due consulenti, stesso nome di portafoglio: nessuna collisione né leakage
    save_portfolio("adv@a", "Client Rossi", {"AAPL": 1000.0}, engine=engine)
    save_portfolio("adv@b", "Client Rossi", {"TSLA": 2000.0}, engine=engine)

    assert list_portfolios("adv@a", engine=engine) == {"Client Rossi": {"AAPL": 1000.0}}
    assert list_portfolios("adv@b", engine=engine) == {"Client Rossi": {"TSLA": 2000.0}}

    # una cancellazione di un consulente non tocca l'altro
    delete_portfolio("adv@a", "Client Rossi", engine=engine)
    assert list_portfolios("adv@a", engine=engine) == {}
    assert list_portfolios("adv@b", engine=engine) == {"Client Rossi": {"TSLA": 2000.0}}


def test_empty_portfolio_name_raises(tmp_path):
    with pytest.raises(ValueError, match="empty"):
        save_portfolio("adv@a", "  ", {"AAPL": 100.0}, engine=_engine(tmp_path))


def test_analysis_history_roundtrip_and_isolation(tmp_path):
    engine = _engine(tmp_path)
    assert load_analyses("adv@a", engine=engine).empty

    log_analysis("adv@a", "Rossi", "1y", 10000.0, 0.184, 72, health=61, engine=engine)
    log_analysis("adv@a", "Rossi", "1y", 10000.0, 0.19, 70, health=64, engine=engine)
    log_analysis("adv@b", "Verdi", "1y", 5000.0, 0.05, 40, health=50, engine=engine)

    history = load_analyses("adv@a", engine=engine)
    assert len(history) == 2  # solo le analisi di adv@a
    assert history.iloc[0]["risk_score"] == 70  # più recente prima
    assert history.iloc[0]["health"] == 64
    assert history.iloc[1]["cum_return"] == pytest.approx(0.184)

    # l'altro consulente vede solo la propria
    other = load_analyses("adv@b", engine=engine)
    assert len(other) == 1
    assert other.iloc[0]["portfolio"] == "Verdi"
