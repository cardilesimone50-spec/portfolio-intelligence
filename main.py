import sys

from src.cli import build_arg_parser, portfolio_from_args
from src.report import generate_report


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    portfolio = portfolio_from_args(args)
    try:
        generate_report(portfolio, period=args.period)
    except ValueError as exc:
        print(f"Errore: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
