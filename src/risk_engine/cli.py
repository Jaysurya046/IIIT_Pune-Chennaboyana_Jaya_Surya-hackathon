"""Command-line diagnostics for the project scaffold."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from risk_engine import __version__
from risk_engine.config import Settings
from risk_engine.ingestion.adapters import FixtureAdapter
from risk_engine.ingestion.models import IngestionRequest
from risk_engine.ingestion.service import IngestionService
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
    fixture_parser = subparsers.add_parser(
        "ingest-fixtures", help="run deterministic news and social fixtures"
    )
    fixture_parser.add_argument("--query", default="financial risk")
    fixture_parser.add_argument("--limit", type=int, default=25)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run a command and return its process exit code."""

    args = build_parser().parse_args(argv)
    settings = Settings.from_env()
    configure_logging(settings.log_level)

    if args.command == "check":
        print(json.dumps(settings.public_summary(), indent=2, sort_keys=True))
        return 0

    if args.command == "ingest-fixtures":
        sample_dir = Path(settings.data_dir) / "sample"
        service = IngestionService(
            [
                FixtureAdapter(sample_dir / "gdelt_articles.json"),
                FixtureAdapter(sample_dir / "bluesky_posts.json"),
            ],
            max_text_length=settings.max_text_length,
        )
        result = service.run(IngestionRequest(query=args.query, limit=args.limit))
        print(result.model_dump_json(indent=2))
        return 0 if result.failed_source_count == 0 else 1

    raise AssertionError(f"Unhandled command: {args.command}")
