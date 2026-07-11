import pandas as pd
import pytest

from src.data.fx import convert_to_eur, is_usd_listing

INDEX = pd.to_datetime(["2026-01-02", "2026-01-05", "2026-01-06"])


def test_is_usd_listing():
    assert is_usd_listing("AAPL") is True
    assert is_usd_listing("BRK.B") is True  # classe azionaria USA, non un mercato
    assert is_usd_listing("ENI.MI") is False
    assert is_usd_listing("AIR.PA") is False
    assert is_usd_listing("SAP.DE") is False


def test_convert_usd_columns_only():
    prices = pd.DataFrame({"AAPL": [110.0, 121.0, 132.0], "ENI.MI": [10.0, 10.0, 10.0]},
                          index=INDEX)
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
