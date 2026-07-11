"""Calcola rendimento e volatilità annualizzati per ogni titolo del Nasdaq-100
a partire dai prezzi salvati in data/nasdaq100_prices.csv (li scarica se assenti)."""

from pathlib import Path

import pandas as pd

from download_nasdaq100 import download_nasdaq100_prices
from src.analytics.performance import per_ticker_annualized_stats
from src.data.cache import load_nasdaq100_prices
from src.portfolio.returns import compute_daily_returns

RESULT_PATH = Path("data/nasdaq100_returns.csv")


def main() -> None:
    prices = load_nasdaq100_prices()
    if prices is None:
        prices = download_nasdaq100_prices()

    returns = compute_daily_returns(prices)
    stats = per_ticker_annualized_stats(returns).sort_values("annual_return", ascending=False)

    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    stats.to_csv(RESULT_PATH)

    with pd.option_context("display.float_format", "{:.2%}".format):
        print(stats)
    print(f"\nSalvato in {RESULT_PATH}")


if __name__ == "__main__":
    main()
