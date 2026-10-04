"""Fondamentali da SEC EDGAR: calcoli su un bilancio sintetico, nessuna rete."""

import pytest

from portfolio_intelligence.data import sec_edgar


def _flow(start, end, val, form="10-Q", filed="2025-08-01"):
    return {"start": start, "end": end, "val": val, "form": form, "filed": filed}


def _instant(end, val, filed="2025-08-01"):
    return {"end": end, "val": val, "form": "10-Q", "filed": filed}


def _series(fy24, fy23, ytd25, ytd24, q225=None, q224=None):
    facts = [
        _flow("2024-01-01", "2024-12-31", fy24, "10-K", "2025-02-01"),
        _flow("2023-01-01", "2023-12-31", fy23, "10-K", "2024-02-01"),
        _flow("2025-01-01", "2025-06-30", ytd25),
        _flow("2024-01-01", "2024-06-30", ytd24),
    ]
    if q225 is not None:
        facts += [_flow("2025-04-01", "2025-06-30", q225), _flow("2024-04-01", "2024-06-30", q224)]
    return {"units": {"USD": facts}}


COMPANY = {
    "entityName": "Example Corp",
    "facts": {
        "us-gaap": {
            # TTM ricavi = 1000 + 600 − 450 = 1150; Q2 su Q2 = 320 / 250 − 1 = 28%
            "RevenueFromContractWithCustomerExcludingAssessedTax": _series(
                1000, 800, 600, 450, 320, 250
            ),
            # tag vecchio, fermo al 2018: non deve essere scelto
            "Revenues": {"units": {"USD": [_flow("2017-01-01", "2017-12-31", 1, "10-K")]}},
            "NetIncomeLoss": _series(200, 150, 150, 100, 80, 50),  # TTM 250
            "GrossProfit": _series(500, 400, 300, 225),  # TTM 575
            "OperatingIncomeLoss": _series(250, 200, 180, 130),  # TTM 300
            "DepreciationDepletionAndAmortization": _series(50, 40, 30, 25),  # TTM 55
            "LongTermDebt": {"units": {"USD": [_instant("2025-06-30", 400)]}},
            "CommercialPaper": {"units": {"USD": [_instant("2025-06-30", 100)]}},
            "StockholdersEquity": {"units": {"USD": [_instant("2025-06-30", 1000)]}},
            "CashAndCashEquivalentsAtCarryingValue": {
                "units": {"USD": [_instant("2025-06-30", 200)]}
            },
            "CommonStockDividendsPerShareDeclared": {
                "units": {
                    "USD/shares": [
                        _flow("2024-01-01", "2024-12-31", 1.0, "10-K", "2025-02-01"),
                        _flow("2025-01-01", "2025-06-30", 0.6),
                        _flow("2024-01-01", "2024-06-30", 0.5),
                    ]
                }
            },
        },
        # due classi di azioni alla stessa data: si sommano (10 + 5)
        "dei": {
            "EntityCommonStockSharesOutstanding": {
                "units": {"shares": [_instant("2025-07-20", 10), _instant("2025-07-20", 5)]}
            }
        },
    },
}


def test_fundamentals_from_facts_computes_ttm_margins_growth_and_multiples():
    row = sec_edgar.fundamentals_from_facts(COMPANY, sic="3571", price=100.0)

    assert row is not None
    assert row["name"] == "Example Corp"
    assert row["sector"] == "Technology"
    assert row["revenue"] == pytest.approx(1150)
    assert row["net_income"] == pytest.approx(250)
    assert row["gross_margin"] == pytest.approx(575 / 1150)
    assert row["operating_margin"] == pytest.approx(300 / 1150)
    assert row["net_margin"] == pytest.approx(250 / 1150)
    assert row["total_debt"] == pytest.approx(500)  # debito a lungo + commercial paper
    assert row["debt_to_equity"] == pytest.approx(50.0)  # in %, come la fonte Yahoo
    assert row["revenue_growth"] == pytest.approx(0.28)
    assert row["earnings_growth"] == pytest.approx(0.6)
    # capitalizzazione = 100 × 15 azioni = 1500
    assert row["pe"] == pytest.approx(1500 / 250)
    assert row["ps"] == pytest.approx(1500 / 1150)
    assert row["ev_ebitda"] == pytest.approx((1500 + 500 - 200) / (300 + 55))
    assert row["dividend_yield"] == pytest.approx(1.1)  # (1.0 + 0.6 − 0.5) / 100, in %
    assert row["forward_pe"] is None


def test_without_price_the_multiples_stay_empty_but_accounting_data_does_not():
    row = sec_edgar.fundamentals_from_facts(COMPANY, sic="3571", price=None)

    assert row is not None and row["revenue"] == pytest.approx(1150)
    assert row["pe"] is None and row["ps"] is None and row["ev_ebitda"] is None


def test_no_usd_revenue_means_no_row():
    """Bilanci IFRS / in altre valute: niente riga, così subentra la fonte di riserva."""
    ifrs = {"entityName": "Foreign NV", "facts": {"ifrs-full": {}}}
    assert sec_edgar.fundamentals_from_facts(ifrs, sic=None, price=10.0) is None


def test_ttm_uses_the_annual_value_when_no_newer_quarter_exists():
    facts = [_flow("2024-01-01", "2024-12-31", 1000, "10-K")]
    assert sec_edgar.ttm(facts) == pytest.approx(1000)


def test_shares_fall_back_to_the_balance_sheet_when_the_cover_page_is_missing():
    company = {
        "facts": {
            "us-gaap": {
                "CommonStockSharesOutstanding": {
                    "units": {"shares": [_instant("2025-03-31", 90), _instant("2025-06-30", 100)]}
                }
            }
        }
    }
    assert sec_edgar.shares_outstanding(company) == pytest.approx(100)


@pytest.mark.parametrize(
    ("sic", "sector"),
    [
        ("3571", "Technology"),
        ("2834", "Healthcare"),
        ("4911", "Utilities"),
        ("5411", "Consumer Defensive"),
        ("6798", "Real Estate"),
        ("6022", "Financial Services"),
        (None, None),
        ("abc", None),
    ],
)
def test_sector_from_sic(sic, sector):
    assert sec_edgar.sector_from_sic(sic) == sector


class _Resp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def test_ticker_to_cik_matches_any_share_class_and_dotted_tickers(monkeypatch):
    seen = []

    def fake_get(_url, params, **_kw):
        seen.append(params["keysTyped"])
        return _Resp(
            {
                "hits": {
                    "hits": [
                        {"_id": "1136101", "_source": {"tickers": None}},
                        {"_id": "1652044", "_source": {"tickers": "GOOG, GOOGL, BRK-B"}},
                    ]
                }
            }
        )

    monkeypatch.setattr(sec_edgar.requests, "get", fake_get)
    sec_edgar.ticker_to_cik.cache_clear()

    assert sec_edgar.ticker_to_cik("GOOGL") == 1652044
    assert sec_edgar.ticker_to_cik("BRK.B") == 1652044
    assert seen[-1] == "BRK-B"  # la SEC scrive le classi con il trattino
    sec_edgar.ticker_to_cik.cache_clear()


def test_fetch_sec_fundamentals_skips_failures_and_tags_the_source(monkeypatch):
    def fake_one(ticker, price=None):
        if ticker == "DOWN":
            raise sec_edgar.requests.ConnectionError("SEC unreachable")
        if ticker == "IFRS":
            return None
        row = sec_edgar.fundamentals_from_facts(COMPANY, "3571", price)
        row["source"] = sec_edgar.SOURCE
        return row

    monkeypatch.setattr(sec_edgar, "fetch_one", fake_one)

    rows = sec_edgar.fetch_sec_fundamentals(["OK", "DOWN", "IFRS"], {"OK": 100.0})

    assert list(rows) == ["OK"]
    assert rows["OK"]["source"] == "SEC EDGAR"
    assert rows["OK"]["pe"] == pytest.approx(6.0)


@pytest.mark.parametrize(
    ("raw", "shown"),
    [("MICROSOFT CORP", "Microsoft Corp"), ("Apple Inc.", "Apple Inc."), (None, None)],
)
def test_display_name_only_fixes_all_caps(raw, shown):
    assert sec_edgar.display_name(raw) == shown
