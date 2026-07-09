"""Parsing degli argomenti da linea di comando per il report di portafoglio."""

import argparse

from src.portfolio import Portfolio


def parse_position(value: str) -> dict:
    try:
        ticker, weight_str = value.split(":")
        return {"ticker": ticker.upper(), "weight": float(weight_str)}
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"Posizione non valida '{value}', usa il formato TICKER:PESO (es. AAPL:0.5)"
        ) from exc


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Genera un report di rendimento e volatilità per un portafoglio."
    )
    parser.add_argument(
        "--position",
        "-p",
        dest="positions",
        action="append",
        required=True,
        type=parse_position,
        help="Posizione nel formato TICKER:PESO, ripetibile (es. -p AAPL:0.5 -p MSFT:0.5)",
    )
    parser.add_argument(
        "--period",
        default="1y",
        help="Periodo storico da scaricare (default: 1y)",
    )
    return parser


def portfolio_from_args(args: argparse.Namespace) -> Portfolio:
    return list(args.positions)
