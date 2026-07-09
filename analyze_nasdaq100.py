"""Calcola rendimento e volatilità annualizzati per ogni titolo del Nasdaq-100
a partire dai prezzi salvati in data/nasdaq100_prices.csv (li scarica se assenti)."""

from pathlib import Path

import pandas as pd

from download_nasdaq100 import OUTPUT_PATH, download_nasdaq100_prices
from src.analytics import compute_daily_returns, per_ticker_annualized_stats

RESULT_PATH = Path("data/nasdaq100_returns.csv")


def load_prices() -> pd.DataFrame:
    if OUTPUT_PATH.exists():
        return pd.read_csv(OUTPUT_PATH, index_col=0, parse_dates=True)
    return download_nasdaq100_prices()


def main() -> None:
    prices = load_prices()
    returns = compute_daily_returns(prices)
    stats = per_ticker_annualized_stats(returns).sort_values("annual_return", ascending=False)

    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    stats.to_csv(RESULT_PATH)

    with pd.option_context("display.float_format", "{:.2%}".format):
        print(stats)
    print(f"\nSalvato in {RESULT_PATH}")


if __name__ == "__main__":
    main()
