import pytest

from portfolio_intelligence.data.store import (
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


def test_positions_with_cost_basis_roundtrip(tmp_path):
    engine = _engine(tmp_path)
    rich = {"AAPL": {"qty": 10.0, "price": 150.5}, "OLD": 500.0}  # nuovo + legacy misti
    save_portfolio("adv@a", "Con carico", rich, engine=engine)
    loaded = list_portfolios("adv@a", engine=engine)["Con carico"]
    assert loaded == rich


def test_delete_portfolio_erases_history_and_client_name_in_audit(tmp_path):
    """Art. 17 GDPR: cancellare un cliente rimuove anche il suo storico analisi
    e il suo nome dall'audit log; i dati di altri clienti e advisor restano."""
    from sqlalchemy import select

    from portfolio_intelligence.data.store import REDACTED, audit_log_table, log_audit

    engine = _engine(tmp_path)
    for advisor in ("adv@a", "adv@b"):
        save_portfolio(advisor, "Client Rossi", {"AAPL": 1000.0}, engine=engine)
        log_analysis(advisor, "Client Rossi", "1y", 1000.0, 0.1, 40, health=70, engine=engine)
        log_audit(advisor, "save_portfolio", "Client Rossi", engine=engine)
    log_analysis("adv@a", "Client Bianchi", "1y", 500.0, 0.0, 30, health=60, engine=engine)

    delete_portfolio("adv@a", "Client Rossi", engine=engine)

    assert list(load_analyses("adv@a", engine=engine)["portfolio"]) == ["Client Bianchi"]
    assert list(load_analyses("adv@b", engine=engine)["portfolio"]) == ["Client Rossi"]
    with engine.connect() as conn:
        rows = conn.execute(select(audit_log_table.c.advisor, audit_log_table.c.detail)).all()
    assert ("adv@a", REDACTED) in rows
    assert ("adv@b", "Client Rossi") in rows


def test_delete_advisor_data_removes_everything_and_pseudonymizes_audit(tmp_path):
    from sqlalchemy import select

    from portfolio_intelligence.data.store import (
        REDACTED,
        audit_log_table,
        delete_advisor_data,
        log_audit,
    )

    engine = _engine(tmp_path)
    save_portfolio("adv@a", "Client Rossi", {"AAPL": 1000.0}, engine=engine)
    log_analysis("adv@a", "Client Rossi", "1y", 1000.0, 0.1, 40, health=70, engine=engine)
    log_audit("adv@a", "save_portfolio", "Client Rossi", engine=engine)
    save_portfolio("adv@b", "Client Verdi", {"MSFT": 1000.0}, engine=engine)

    counts = delete_advisor_data("adv@a", engine=engine)

    assert counts == {"portfolios": 1, "analyses": 1, "audit_pseudonymized": 1}
    assert list_portfolios("adv@a", engine=engine) == {}
    assert load_analyses("adv@a", engine=engine).empty
    assert list_portfolios("adv@b", engine=engine) == {"Client Verdi": {"MSFT": 1000.0}}
    with engine.connect() as conn:
        advisor, detail = conn.execute(
            select(audit_log_table.c.advisor, audit_log_table.c.detail)
        ).one()
    assert advisor.startswith("deleted:") and "adv@a" not in advisor
    assert detail == REDACTED


def test_client_risk_profile_is_stored_and_kept_when_positions_change(tmp_path):
    from portfolio_intelligence.data.store import list_clients

    engine = _engine(tmp_path)
    save_portfolio("adv@a", "C-001", {"AAPL": 100.0}, engine=engine, risk_profile="Moderate")
    save_portfolio("adv@a", "C-001", {"MSFT": 50.0}, engine=engine)  # senza profilo: resta
    save_portfolio("adv@a", "C-002", {"NVDA": 10.0}, engine=engine)

    clients = list_clients("adv@a", engine=engine)

    assert clients["C-001"]["risk_profile"] == "Moderate"
    assert clients["C-001"]["positions"] == {"MSFT": 50.0}
    assert clients["C-002"]["risk_profile"] == "Not set"
    assert list_clients("adv@b", engine=engine) == {}  # isolamento per consulente


# ---------------------------------------------------- record storici e profilo di rischio


def _insert_raw(engine, advisor, name, positions_json, profile):
    """Simula un record scritto prima della migrazione (o a mano sul DB)."""
    from sqlalchemy import text

    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO portfolios (advisor, name, positions, updated, risk_profile) "
                "VALUES (:a, :n, :p, '2025-01-01T00:00:00', :r)"
            ),
            {"a": advisor, "n": name, "p": positions_json, "r": profile},
        )


def test_legacy_record_without_profile_and_with_old_positions_loads_safely(tmp_path):
    from portfolio_intelligence.data.store import list_clients

    engine = _engine(tmp_path)
    _insert_raw(engine, "adv@a", "LEGACY", '{"AAPL": 1000.0}', None)

    clients = list_clients("adv@a", engine=engine)
    assert clients["LEGACY"]["risk_profile"] == "Not set"  # mai None verso le viste
    assert clients["LEGACY"]["positions"] == {"AAPL": 1000.0}
    assert list_portfolios("adv@a", engine=engine) == {"LEGACY": {"AAPL": 1000.0}}


def test_unknown_profile_value_falls_back_to_not_set(tmp_path):
    from portfolio_intelligence.data.store import list_clients

    engine = _engine(tmp_path)
    _insert_raw(engine, "adv@a", "ODD", '{"AAPL": 1.0}', "balanced")

    assert list_clients("adv@a", engine=engine)["ODD"]["risk_profile"] == "Not set"


def test_saving_an_unknown_profile_is_rejected(tmp_path):
    engine = _engine(tmp_path)
    with pytest.raises(ValueError, match="risk profile"):
        save_portfolio("adv@a", "C-1", {"AAPL": 1.0}, engine=engine, risk_profile="balanced")


def test_create_client_never_overwrites_an_existing_code(tmp_path):
    from portfolio_intelligence.data.store import ClientExistsError, create_client, list_clients

    engine = _engine(tmp_path)
    create_client("adv@a", "C-1", {"AAPL": 1.0}, "Aggressive", engine=engine)

    with pytest.raises(ClientExistsError):
        create_client("adv@a", "C-1 ", {"MSFT": 2.0}, "Conservative", engine=engine)
    create_client("adv@b", "C-1", {"NVDA": 3.0}, "Moderate", engine=engine)  # altro consulente: ok

    assert list_clients("adv@a", engine=engine)["C-1"]["risk_profile"] == "Aggressive"
    assert list_clients("adv@a", engine=engine)["C-1"]["positions"] == {"AAPL": 1.0}
    assert list_clients("adv@b", engine=engine)["C-1"]["risk_profile"] == "Moderate"
