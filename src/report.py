"""Genera un report di rendimento e volatilità per un portafoglio."""

from src.analytics import (
    compute_daily_returns,
    portfolio_expected_return,
    portfolio_volatility,
)
from src.market_data import fetch_price_history
from src.portfolio import Portfolio, weights_sum_to_one


def generate_report(portfolio: Portfolio, period: str = "1y") -> None:
    if not weights_sum_to_one(portfolio):
        raise ValueError("I pesi del portafoglio devono sommare a 1")

    tickers = [position["ticker"] for position in portfolio]
    prices = fetch_price_history(tickers, period=period)
    returns = compute_daily_returns(prices)

    expected_return = portfolio_expected_return(returns, portfolio)
    volatility = portfolio_volatility(returns, portfolio)

    print(f"Portafoglio ({period}):")
    for position in portfolio:
        print(f"  {position['ticker']}: {position['weight']:.1%}")
    print(f"Rendimento medio giornaliero atteso: {expected_return:.4%}")
    print(f"Volatilità giornaliera: {volatility:.4%}")
