"""Test del parser Fineco su testo SINTETICO che imita il layout reale.

Nessun dato personale e nessun PDF reale nel repo: si testa la funzione pura
`extract_holdings`, che è dove vive tutta la logica.
"""

import pytest

from src.data.fineco import extract_holdings, resolve_to_positions
from src.data.isin import SecurityRef

# imita la pagina «Strumenti finanziari», comprese le intestazioni di pagina
# che si intromettono nella tabella e una riga DOPO il totale (da ignorare).
STATEMENT = """Estratto conto Ottobre - Novembre - Dicembre 2024
PAGINA 9 DI 10
? Strumenti finanziari Situazione al 31.12.2024
6318155/01
CODICE TITOLO DIVISA RATEO QUANTITA' PREZZO CONTROVALORE
IT0005083057 Btp Test 3,25% 7.000,000 0 EUR 94,53801 89,99650 1,08633 1,00 1,00 6.375,80
US0378331005 Apple Inc 10,000 0 USD 200,00000 190,00000 - 1,05 1,04 1.800,50
PAGINA 10 DI 10
US5949181045 Microsoft Corp 5,000 0 EUR 400,00 350,00 - 1,00 1,00 1.750,00
Totale in euro 9.926,30
US88160R1014 Tesla 11,000 0 USD 467,96 403,84 - 1,04 1,03 4.275,91
"""


def test_extracts_all_holdings_in_section():
    holdings = extract_holdings(STATEMENT)
    assert [h.isin for h in holdings] == [
        "IT0005083057",
        "US0378331005",
        "US5949181045",
    ]


def test_stops_at_total_line():
    # la riga Tesla è dopo «Totale in euro»: non deve essere inclusa
    holdings = extract_holdings(STATEMENT)
    assert all(h.isin != "US88160R1014" for h in holdings)


def test_market_value_is_last_number_not_a_price_column():
    holdings = {h.isin: h for h in extract_holdings(STATEMENT)}
    assert holdings["IT0005083057"].market_value_eur == pytest.approx(6375.80)
    assert holdings["US0378331005"].market_value_eur == pytest.approx(1800.50)
    assert holdings["US5949181045"].market_value_eur == pytest.approx(1750.00)


def test_currency_detection():
    holdings = {h.isin: h for h in extract_holdings(STATEMENT)}
    assert holdings["US0378331005"].currency == "USD"
    assert holdings["US5949181045"].currency == "EUR"
    assert holdings["IT0005083057"].currency == "EUR"


def test_name_truncated_before_numbers_even_with_percent():
    holdings = {h.isin: h for h in extract_holdings(STATEMENT)}
    # «Btp Test 3,25%» → il nome si ferma prima del primo numero (3,25)
    assert holdings["IT0005083057"].name == "Btp Test"
    assert holdings["US0378331005"].name == "Apple Inc"


def test_content_before_section_is_ignored():
    text = "IT9999999999 Fuori sezione 1,000 EUR 1.000,00\n" + STATEMENT
    holdings = extract_holdings(text)
    assert all(h.isin != "IT9999999999" for h in holdings)


def test_no_section_returns_empty():
    assert extract_holdings("Solo movimenti di conto, nessun titolo.\n") == []


def test_resolve_to_positions_maps_isin_and_reports_skipped():
    holdings = extract_holdings(STATEMENT)  # 2 azioni (Apple, Microsoft) + 1 BTP

    def fake_resolver(isins):
        # OpenFIGI risolve le azioni, non l'obbligazione italiana
        table = {
            "US0378331005": SecurityRef("US0378331005", "AAPL", "US", "APPLE INC"),
            "US5949181045": SecurityRef("US5949181045", "MSFT", "US", "MICROSOFT CORP"),
        }
        return {i: table[i] for i in isins if i in table}

    positions, skipped = resolve_to_positions(holdings, resolver=fake_resolver)

    assert positions == {"AAPL": pytest.approx(1800.50), "MSFT": pytest.approx(1750.00)}
    assert [h.isin for h in skipped] == ["IT0005083057"]  # il BTP non prezzabile


def test_resolve_to_positions_skips_resolved_but_non_equity_bond():
    # un BTP viene risolto da OpenFIGI, ma a un identificativo obbligazionario
    # (marketSector 'Govt'): non è prezzabile dal motore azionario → skipped
    holdings = extract_holdings(STATEMENT)

    def resolver(isins):
        out = {}
        for i in isins:
            if i == "IT0005083057":
                out[i] = SecurityRef(i, "BTPS 3.25", "", "BTP", market_sector="Govt")
            elif i == "US0378331005":
                out[i] = SecurityRef(i, "AAPL", "US", "APPLE INC", market_sector="Equity")
        return out

    positions, skipped = resolve_to_positions(holdings, resolver=resolver)
    assert positions == {"AAPL": pytest.approx(1800.50)}
    assert [h.isin for h in skipped] == ["IT0005083057", "US5949181045"]  # bond + non risolto


def test_resolve_to_positions_sums_duplicate_tickers():
    holdings = extract_holdings(STATEMENT)

    def resolver(isins):
        # entrambe le azioni collassano sullo stesso ticker → importi sommati
        return {
            i: SecurityRef(i, "SAME", "US", "X")
            for i in isins
            if i in {"US0378331005", "US5949181045"}
        }

    positions, _ = resolve_to_positions(holdings, resolver=resolver)
    assert positions == {"SAME": pytest.approx(1800.50 + 1750.00)}
