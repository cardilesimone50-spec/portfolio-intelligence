import io

import pandas as pd
import pytest

from src.data.importers import parse_positions


def test_parse_csv_basic():
    content = b"ticker,importo\nAAPL,4000\nmsft,3000\n"
    assert parse_positions(content, "broker.csv") == {"AAPL": 4000.0, "MSFT": 3000.0}


def test_parse_csv_italian_format_and_synonyms():
    content = "Titolo;Controvalore\nAAPL;1.234,56 €\nNVDA;2.000,00\n".encode()
    positions = parse_positions(content, "estratto.csv")
    assert positions["AAPL"] == pytest.approx(1234.56)
    assert positions["NVDA"] == pytest.approx(2000.0)


def test_parse_sums_duplicates_and_skips_invalid_rows():
    content = b"ticker,importo\nAAPL,1000\nAAPL,500\nMSFT,not-a-number\nTSLA,-50\n"
    assert parse_positions(content, "x.csv") == {"AAPL": 1500.0}


def test_parse_excel():
    buffer = io.BytesIO()
    pd.DataFrame({"Symbol": ["AAPL"], "Amount": [2500]}).to_excel(buffer, index=False)
    positions = parse_positions(buffer.getvalue(), "broker.xlsx")
    assert positions == {"AAPL": 2500.0}


def test_parse_csv_with_broker_preamble():
    content = (
        "Estratto conto titoli\nData: 10/07/2026\n\n"
        "Simbolo;Quantità;Prezzo\nAAPL;10;200,50\nMSFT;5;300,00\n"
    ).encode()
    positions = parse_positions(content, "fineco.csv")
    assert positions["AAPL"] == pytest.approx(2005.0)
    assert positions["MSFT"] == pytest.approx(1500.0)


def test_parse_quantity_times_price_fallback():
    content = b"ticker,quantity,price\nNVDA,4,180.5\n"
    assert parse_positions(content, "x.csv") == {"NVDA": pytest.approx(722.0)}


def test_unrecognized_columns_raise():
    with pytest.raises(ValueError, match="Unrecognized columns"):
        parse_positions(b"a,b\n1,2\n", "x.csv")


def test_unsupported_extension_raises():
    with pytest.raises(ValueError, match="Unsupported format"):
        parse_positions(b"", "portafoglio.pdf")


def test_parse_quantity_and_cost_price_returns_positions_with_pnl_basis():
    content = "ticker,quantità,prezzo medio di carico,controvalore\nAAPL,10,\"150,50\",2000\n".encode()
    positions = parse_positions(content, "fineco.csv")
    # con quantità + prezzo di carico il controvalore viene ignorato:
    # vince il formato ricco che permette il P&L reale
    assert positions == {"AAPL": {"qty": 10.0, "price": 150.5}}


def test_duplicate_lots_average_the_cost_price():
    content = b"ticker,quantity,avg price\nAAPL,10,100\nAAPL,10,200\n"
    positions = parse_positions(content, "lots.csv")
    assert positions["AAPL"]["qty"] == 20.0
    assert positions["AAPL"]["price"] == 150.0
