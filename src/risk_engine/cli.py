"""Command-line diagnostics for the project scaffold."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence

from risk_engine import __version__
from risk_engine.config import Settings
from risk_engine.logging_config import configure_logging


def build_parser() -> argparse.ArgumentParser:
    """Create the command-line parser."""

    parser = argparse.ArgumentParser(
        prog="risksignal",
        description="RiskSignal Engine development commands",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("check", help="validate configuration and print a safe summary")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run a command and return its process exit code."""

    args = build_parser().parse_args(argv)
    settings = Settings.from_env()
    configure_logging(settings.log_level)

    if args.command == "check":
        print(json.dumps(settings.public_summary(), indent=2, sort_keys=True))
        return 0

    raise AssertionError(f"Unhandled command: {args.command}")
