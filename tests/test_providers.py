import pandas as pd
import pytest

from src.data.providers import (
    EODHDProvider,
    ProviderChain,
    ProviderError,
    YahooChartProvider,
    build_default_chain,
)


class _ChartResp:
    def __init__(self, payload, status=200):
        self.status_code = status
        self._payload = payload

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests

            raise requests.HTTPError(str(self.status_code))

    def json(self):
        return self._payload


def _chart_payload(adjclose=None, close=None, ts=(1704153600, 1704240000)):
    indicators = {"quote": [{"close": close if close is not None else [None] * len(ts)}]}
    if adjclose is not None:
        indicators["adjclose"] = [{"adjclose": adjclose}]
    return {"chart": {"result": [{"timestamp": list(ts), "indicators": indicators}]}}


class _StubProvider:
    def __init__(self, name, result=None, fail=False):
        self.name = name
        self._result = result
        self._fail = fail
        self.called = False

    def fetch(self, tickers, period):
        self.called = True
        if self._fail:
            raise ProviderError(f"{self.name} down")
        return self._result


def test_chain_returns_first_successful():
    good = pd.DataFrame({"AAPL": [1.0, 2.0]})
    chain = ProviderChain([_StubProvider("Primary", result=good)])
    data, source = chain.fetch(["AAPL"], "1y")
    assert source == "Primary"
    assert data.equals(good)


def test_chain_falls_back_when_provider_fails():
    good = pd.DataFrame({"AAPL": [1.0, 2.0]})
    primary = _StubProvider("Primary", fail=True)
    secondary = _StubProvider("Secondary", result=good)
    chain = ProviderChain([primary, secondary])

    data, source = chain.fetch(["AAPL"], "1y")
    assert primary.called and secondary.called
    assert source == "Secondary"


def test_chain_skips_empty_results():
    empty = pd.DataFrame({"AAPL": [float("nan")]})
    good = pd.DataFrame({"AAPL": [1.0]})
    chain = ProviderChain([_StubProvider("A", result=empty), _StubProvider("B", result=good)])
    _, source = chain.fetch(["AAPL"], "1y")
    assert source == "B"


def test_chain_raises_when_all_fail():
    chain = ProviderChain([_StubProvider("A", fail=True), _StubProvider("B", fail=True)])
    with pytest.raises(ValueError, match="No data provider"):
        chain.fetch(["AAPL"], "1y")


def test_default_chain_prepends_eodhd_when_key_present(monkeypatch):
    monkeypatch.setenv("EODHD_API_KEY", "secret")
    chain = build_default_chain()
    assert chain.active_source == "EODHD"


def test_default_chain_without_key_starts_with_yahoo_chart(monkeypatch):
    monkeypatch.delenv("EODHD_API_KEY", raising=False)
    chain = build_default_chain()
    # Yahoo chart (HTTP) è il primo tra i gratuiti: regge meglio sul cloud
    assert chain.active_source == "Yahoo (chart)"


def test_yahoo_chart_parses_adjusted_close(monkeypatch):
    monkeypatch.setattr(
        "src.data.providers.requests.get",
        lambda *a, **k: _ChartResp(_chart_payload(adjclose=[99.0, 100.5])),
    )
    df = YahooChartProvider(backoff=0).fetch(["AAPL"], "1y")
    assert df["AAPL"].tolist() == [99.0, 100.5]


def test_yahoo_chart_falls_back_to_close_without_adjclose(monkeypatch):
    monkeypatch.setattr(
        "src.data.providers.requests.get",
        lambda *a, **k: _ChartResp(_chart_payload(close=[10.0, 11.0])),
    )
    df = YahooChartProvider(backoff=0).fetch(["AAPL"], "1y")
    assert df["AAPL"].tolist() == [10.0, 11.0]


def test_yahoo_chart_retries_on_429_then_succeeds(monkeypatch):
    calls = {"n": 0}

    def fake_get(*_a, **_k):
        calls["n"] += 1
        if calls["n"] == 1:
            return _ChartResp({}, status=429)
        return _ChartResp(_chart_payload(adjclose=[5.0, 6.0]))

    monkeypatch.setattr("src.data.providers.requests.get", fake_get)
    df = YahooChartProvider(backoff=0).fetch(["AAPL"], "1y")
    assert calls["n"] == 2
    assert df["AAPL"].tolist() == [5.0, 6.0]


def test_yahoo_chart_raises_when_no_result(monkeypatch):
    monkeypatch.setattr(
        "src.data.providers.requests.get",
        lambda *a, **k: _ChartResp({"chart": {"result": None}}),
    )
    with pytest.raises(ProviderError):
        YahooChartProvider(backoff=0).fetch(["AAPL"], "1y")


def test_eodhd_parses_adjusted_close(monkeypatch):
    provider = EODHDProvider("key")

    class FakeResp:
        def raise_for_status(self):
            pass

        def json(self):
            return [
                {"date": "2026-01-02", "close": 100.0, "adjusted_close": 99.0},
                {"date": "2026-01-03", "close": 101.0, "adjusted_close": 100.5},
            ]

    monkeypatch.setattr("src.data.providers.requests.get", lambda *a, **k: FakeResp())
    df = provider.fetch(["AAPL"], "1y")
    assert df["AAPL"].tolist() == [99.0, 100.5]  # usa adjusted_close
