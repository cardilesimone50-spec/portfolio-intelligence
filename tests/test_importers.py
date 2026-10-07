import io

import pandas as pd
import pytest

from portfolio_intelligence.data.importers import parse_positions


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
    content = (
        'ticker,quantità,prezzo medio di carico,controvalore\nAAPL,10,"150,50",2000\n'.encode()
    )
    positions = parse_positions(content, "fineco.csv")
    # con quantità + prezzo di carico il controvalore viene ignorato:
    # vince il formato ricco che permette il P&L reale
    assert positions == {"AAPL": {"qty": 10.0, "price": 150.5}}


def test_duplicate_lots_average_the_cost_price():
    content = b"ticker,quantity,avg price\nAAPL,10,100\nAAPL,10,200\n"
    positions = parse_positions(content, "lots.csv")
    assert positions["AAPL"]["qty"] == 20.0
    assert positions["AAPL"]["price"] == 150.0


# ------------------------------------------------ sicurezza: nessun testo arbitrario come ticker


def test_import_drops_rows_whose_ticker_is_not_a_market_symbol():
    payload = '<iframe srcdoc="x">'
    content = f"Ticker;Controvalore\nAAPL;1000\n{payload};500\nENI.MI;300\n".encode()
    positions = parse_positions(content, "pos.csv")
    assert set(positions) == {"AAPL", "ENI.MI"}


def test_saved_portfolios_with_markup_tickers_are_cleaned_on_load():
    from portfolio_intelligence.portfolio.positions import normalize_portfolio

    cleaned = normalize_portfolio({"AAPL": 1000.0, "Y<IFRAME SRCDOC=X>": 10.0, "BRK.B": 5.0})
    assert set(cleaned) == {"AAPL", "BRK.B"}


def test_client_codes_cannot_carry_markup(tmp_path):
    import pytest

    from portfolio_intelligence.data.store import create_client, get_engine

    engine = get_engine(f"sqlite:///{tmp_path / 'c.db'}")
    with pytest.raises(ValueError):
        create_client("adv@x", "<img src=x>", {"AAPL": 1.0}, engine=engine)
    create_client("adv@x", "Rossi - C/42", {"AAPL": 1.0}, engine=engine)


def test_position_cards_escape_provider_names():
    from portfolio_intelligence.ui.components import position_card_html

    html_text = position_card_html("AAPL", 100.0, 0.5, "#123456", company="<b>x</b> & co")
    assert "<b>x</b>" not in html_text and "&lt;b&gt;x&lt;/b&gt; &amp; co" in html_text


def test_to_number_reads_italian_and_english_formats():
    from portfolio_intelligence.data.importers import _to_number

    assert _to_number("1.234,56 €") == 1234.56
    assert _to_number("$2,275.20") == 2275.20
    assert _to_number("1,200,000") == 1_200_000
    assert _to_number("12,5") == 12.5
    assert _to_number("1.200.000") == 1_200_000
