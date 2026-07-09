import argparse

import pytest

from src.cli import build_arg_parser, parse_position, portfolio_from_args


def test_parse_position_valid():
    assert parse_position("aapl:0.5") == {"ticker": "AAPL", "weight": 0.5}


def test_parse_position_invalid_format():
    with pytest.raises(argparse.ArgumentTypeError):
        parse_position("AAPL-0.5")


def test_parse_position_invalid_weight():
    with pytest.raises(argparse.ArgumentTypeError):
        parse_position("AAPL:not-a-number")


def test_portfolio_from_args():
    parser = build_arg_parser()
    args = parser.parse_args(["-p", "AAPL:0.5", "-p", "MSFT:0.5", "--period", "6mo"])
    portfolio = portfolio_from_args(args)
    assert portfolio == [
        {"ticker": "AAPL", "weight": 0.5},
        {"ticker": "MSFT", "weight": 0.5},
    ]
    assert args.period == "6mo"
