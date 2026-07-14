import pytest
import requests

from src.data.yahoo_client import get_nasdaq100_tickers

FAKE_HTML = """
<table>
<tr><th>#</th><th>Company</th><th>Symbol</th><th>Weight</th></tr>
<tr><td>1</td><td>Example Corp</td><td>EXMP</td><td>10.0%</td></tr>
<tr><td>2</td><td>Sample Inc</td><td>SMPL</td><td>5.0%</td></tr>
</table>
"""


class FakeResponse:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        pass


def test_get_nasdaq100_tickers_parses_symbols(monkeypatch):
    monkeypatch.setattr(
        "src.data.yahoo_client.requests.get", lambda url, headers, timeout: FakeResponse(FAKE_HTML)
    )
    tickers = get_nasdaq100_tickers()
    assert tickers == ["EXMP", "SMPL"]


def test_get_nasdaq100_tickers_network_error_raises(monkeypatch):
    def fake_get(url, headers, timeout):
        raise requests.exceptions.ConnectionError("boom")

    monkeypatch.setattr("src.data.yahoo_client.requests.get", fake_get)

    with pytest.raises(ValueError, match="Network error"):
        get_nasdaq100_tickers()
