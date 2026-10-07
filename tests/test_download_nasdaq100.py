import pandas as pd

from download_nasdaq100 import readjusted_tickers


def test_split_readjustment_is_detected_on_the_overlap_day():
    day = pd.Timestamp("2026-06-10")
    stored = pd.DataFrame({"NVDA": [1200.0], "AAPL": [200.0]}, index=[day])
    # dopo un frazionamento 10:1 Yahoo ricalcola tutto lo storico rettificato
    update = pd.DataFrame(
        {"NVDA": [120.0, 121.0], "AAPL": [200.0, 201.0]}, index=[day, day + pd.Timedelta(days=1)]
    )
    assert readjusted_tickers(stored, update, day) == ["NVDA"]


def test_no_overlap_means_nothing_to_redownload():
    stored = pd.DataFrame({"AAPL": [200.0]}, index=[pd.Timestamp("2026-06-09")])
    update = pd.DataFrame({"AAPL": [201.0]}, index=[pd.Timestamp("2026-06-10")])
    assert readjusted_tickers(stored, update, pd.Timestamp("2026-06-10")) == []
