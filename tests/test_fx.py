import pandas as pd
import pytest

from portfolio_intelligence.data import fx
from portfolio_intelligence.data.fx import convert_to_eur, is_usd_listing

INDEX = pd.to_datetime(["2026-01-02", "2026-01-05", "2026-01-06"])


def test_is_usd_listing():
    assert is_usd_listing("AAPL") is True
    assert is_usd_listing("BRK.B") is True  # classe azionaria USA, non un mercato
    assert is_usd_listing("ENI.MI") is False
    assert is_usd_listing("AIR.PA") is False
    assert is_usd_listing("SAP.DE") is False


def test_convert_usd_columns_only():
    prices = pd.DataFrame(
        {"AAPL": [110.0, 121.0, 132.0], "ENI.MI": [10.0, 10.0, 10.0]}, index=INDEX
    )
    eurusd = pd.Series([1.10, 1.10, 1.20], index=INDEX)

    converted = convert_to_eur(prices, eurusd)

    assert converted["AAPL"].tolist() == pytest.approx([100.0, 110.0, 110.0])
    assert converted["ENI.MI"].tolist() == pytest.approx([10.0, 10.0, 10.0])  # già in EUR


def test_fx_gap_is_forward_filled():
    prices = pd.DataFrame({"AAPL": [110.0, 110.0, 110.0]}, index=INDEX)
    eurusd = pd.Series([1.10, 1.10], index=INDEX[:2])  # manca l'ultimo giorno

    converted = convert_to_eur(prices, eurusd)

    assert converted["AAPL"].iloc[-1] == pytest.approx(100.0)


def test_fx_changes_eur_returns_even_with_flat_usd_prices():
    # prezzo USD fermo ma dollaro che si indebolisce: in EUR l'investitore perde
    prices = pd.DataFrame({"AAPL": [100.0, 100.0, 100.0]}, index=INDEX)
    eurusd = pd.Series([1.00, 1.10, 1.20], index=INDEX)

    converted = convert_to_eur(prices, eurusd)

    assert converted["AAPL"].iloc[-1] < converted["AAPL"].iloc[0]


class _Resp:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        pass


ECB_CSV = (
    "KEY,FREQ,CURRENCY,CURRENCY_DENOM,EXR_TYPE,EXR_SUFFIX,TIME_PERIOD,OBS_VALUE,OBS_STATUS\n"
    "EXR.D.USD.EUR.SP00.A,D,USD,EUR,SP00,A,2026-09-29,1.1355,A\n"
    "EXR.D.USD.EUR.SP00.A,D,USD,EUR,SP00,A,2026-09-28,1.1378,A\n"
)


def test_ecb_parser_returns_sorted_usd_per_eur_series(monkeypatch):
    monkeypatch.setattr(fx.requests, "get", lambda *a, **k: _Resp(ECB_CSV))

    series = fx.fetch_eurusd_ecb("1mo")

    assert list(series.index) == list(pd.to_datetime(["2026-09-28", "2026-09-29"]))
    assert series.tolist() == pytest.approx([1.1378, 1.1355])


def test_fetch_eurusd_prefers_ecb_and_falls_back_to_yahoo(monkeypatch):
    ecb = pd.Series([1.10], index=INDEX[:1])
    yahoo = pd.DataFrame({fx.EURUSD_TICKER: [1.20]}, index=INDEX[:1])
    monkeypatch.setattr(
        "portfolio_intelligence.data.providers.YahooChartProvider.fetch",
        lambda _self, _t, _p: yahoo,
    )

    monkeypatch.setattr(fx, "fetch_eurusd_ecb", lambda _period: ecb)
    assert fx.fetch_eurusd("1y").iloc[0] == pytest.approx(1.10)

    def _ecb_down(_period):
        raise RuntimeError("ECB unreachable")

    monkeypatch.setattr(fx, "fetch_eurusd_ecb", _ecb_down)
    assert fx.fetch_eurusd("1y").iloc[0] == pytest.approx(1.20)
