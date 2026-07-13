import pandas as pd
import pytest

from src.data.providers import (
    EODHDProvider,
    ProviderChain,
    ProviderError,
    build_default_chain,
)


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
    with pytest.raises(ValueError, match="Nessun provider"):
        chain.fetch(["AAPL"], "1y")


def test_default_chain_prepends_eodhd_when_key_present(monkeypatch):
    monkeypatch.setenv("EODHD_API_KEY", "secret")
    chain = build_default_chain()
    assert chain.active_source == "EODHD"


def test_default_chain_without_key_starts_with_yahoo(monkeypatch):
    monkeypatch.delenv("EODHD_API_KEY", raising=False)
    chain = build_default_chain()
    assert chain.active_source == "Yahoo Finance"


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
