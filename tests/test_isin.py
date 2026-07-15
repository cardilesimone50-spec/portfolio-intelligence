import pytest
import requests

from src.data.isin import IsinError, resolve_isin, resolve_isins


class _FakeResp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


# database ISIN → listing candidates (come li restituisce OpenFIGI)
_DB = {
    "US0378331005": [
        {"ticker": "AAPL", "exchCode": "US", "securityType": "Common Stock", "name": "APPLE INC", "marketSector": "Equity"},
        {"ticker": "AAPL", "exchCode": "MM", "securityType": "Common Stock", "name": "APPLE INC", "marketSector": "Equity"},
    ],
    "IT0003128367": [
        {"ticker": "ENEL", "exchCode": "MI", "securityType": "Common Stock", "name": "ENEL SPA"},
    ],
    # stesso ISIN con un derivato su piazza USA e l'azione ordinaria: vince l'azione
    "US88160R1014": [
        {"ticker": "TSLA", "exchCode": "US", "securityType": "Equity WRT", "name": "TESLA WARRANT"},
        {"ticker": "TSLA", "exchCode": "US", "securityType": "Common Stock", "name": "TESLA INC"},
    ],
}


def _fake_post(url, json=None, headers=None, timeout=None):
    payload = []
    for job in json:
        candidates = _DB.get(job["idValue"])
        payload.append({"data": candidates} if candidates else {"warning": "No identifier found."})
    return _FakeResp(payload)


def test_resolve_single_isin():
    ref = resolve_isin("US0378331005", post=_fake_post)
    assert ref is not None
    assert ref.ticker == "AAPL"
    assert ref.isin == "US0378331005"
    assert ref.name == "APPLE INC"


def test_resolve_prefers_us_exchange_over_others():
    ref = resolve_isin("US0378331005", post=_fake_post)
    assert ref.exchange == "US"  # non "MM"


def test_resolved_equity_is_marked_priceable():
    ref = resolve_isin("US0378331005", post=_fake_post)
    assert ref.market_sector == "Equity"
    assert ref.is_priceable_equity is True


def test_resolve_prefers_common_stock_over_derivative():
    ref = resolve_isin("US88160R1014", post=_fake_post)
    assert ref.name == "TESLA INC"


def test_resolve_italian_listing():
    ref = resolve_isin("IT0003128367", post=_fake_post)
    assert ref.ticker == "ENEL"
    assert ref.exchange == "MI"


def test_unresolved_isin_is_omitted():
    result = resolve_isins(["US0378331005", "XX0000000000"], post=_fake_post)
    assert set(result) == {"US0378331005"}


def test_empty_input_returns_empty():
    assert resolve_isins([], post=_fake_post) == {}


def test_normalizes_case_and_whitespace():
    ref = resolve_isin("  us0378331005 ", post=_fake_post)
    assert ref is not None and ref.ticker == "AAPL"


def test_batches_more_than_ten_isins():
    calls = {"n": 0}

    def counting_post(url, json=None, headers=None, timeout=None):
        calls["n"] += 1
        assert len(json) <= 10  # rispetta il limite anonimo per chiamata
        return _fake_post(url, json=json, headers=headers, timeout=timeout)

    isins = ["US0378331005"] * 12  # 12 job → 2 chiamate (10 + 2)
    result = resolve_isins(isins, post=counting_post)
    assert calls["n"] == 2
    assert "US0378331005" in result


def test_network_error_raises_isin_error():
    def boom(*_args, **_kwargs):
        raise requests.ConnectionError("down")

    with pytest.raises(IsinError):
        resolve_isins(["US0378331005"], post=boom)
