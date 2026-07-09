from src.portfolio import Portfolio
from src.report import generate_report

PORTFOLIO: Portfolio = [
    {"ticker": "AAPL", "weight": 0.5},
    {"ticker": "MSFT", "weight": 0.5},
]

if __name__ == "__main__":
    generate_report(PORTFOLIO)
