"""Report dei fondamentali (ricavi, utili, margini, debito, crescita, multipli)
per una lista di ticker passata da linea di comando."""

import argparse
import sys

from src.fundamentals.valuation import fetch_fundamentals


def _fmt_money(value: float | None) -> str:
    if value is None or value != value:
        return "n/d"
    for unit, divisor in (("T", 1e12), ("B", 1e9), ("M", 1e6)):
        if abs(value) >= divisor:
            return f"{value / divisor:.1f}{unit}"
    return f"{value:.0f}"


def _fmt_pct(value: float | None) -> str:
    if value is None or value != value:
        return "n/d"
    return f"{value:.1%}"


def _fmt_ratio(value: float | None) -> str:
    if value is None or value != value:
        return "n/d"
    return f"{value:.1f}"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Mostra i fondamentali e i multipli di valutazione per uno o più ticker."
    )
    parser.add_argument("tickers", nargs="+", help="Ticker da analizzare (es. AAPL MSFT NVDA)")
    args = parser.parse_args()

    try:
        data = fetch_fundamentals([t.upper() for t in args.tickers])
    except ValueError as exc:
        print(f"Errore: {exc}", file=sys.stderr)
        sys.exit(1)

    for ticker, row in data.iterrows():
        print(f"\n{ticker} — {row['name']}")
        print(f"  Ricavi (TTM):        {_fmt_money(row['revenue'])}")
        print(f"  Utile netto (TTM):   {_fmt_money(row['net_income'])}")
        print(f"  Margine lordo:       {_fmt_pct(row['gross_margin'])}")
        print(f"  Margine operativo:   {_fmt_pct(row['operating_margin'])}")
        print(f"  Margine netto:       {_fmt_pct(row['net_margin'])}")
        print(f"  Debito totale:       {_fmt_money(row['total_debt'])}")
        print(f"  Debito/Equity:       {_fmt_ratio(row['debt_to_equity'])}")
        print(f"  Crescita ricavi:     {_fmt_pct(row['revenue_growth'])}")
        print(f"  Crescita utili:      {_fmt_pct(row['earnings_growth'])}")
        print(f"  P/E:                 {_fmt_ratio(row['pe'])}")
        print(f"  P/E forward:         {_fmt_ratio(row['forward_pe'])}")
        print(f"  EV/EBITDA:           {_fmt_ratio(row['ev_ebitda'])}")
        print(f"  P/S:                 {_fmt_ratio(row['ps'])}")


if __name__ == "__main__":
    main()
