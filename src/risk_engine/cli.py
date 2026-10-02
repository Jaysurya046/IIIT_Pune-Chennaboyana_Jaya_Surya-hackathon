"""Command-line diagnostics for the project scaffold."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

from risk_engine import __version__
from risk_engine.config import Settings
from risk_engine.ingestion.adapters import FixtureAdapter
from risk_engine.ingestion.models import IngestionRequest
from risk_engine.ingestion.service import IngestionService
from risk_engine.logging_config import configure_logging
from risk_engine.nlp.factory import build_risk_engine
from risk_engine.stress.factory import build_stress_engine


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
    analyze_parser = subparsers.add_parser(
        "analyze-fixtures", help="generate risk signals from deterministic source fixtures"
    )
    analyze_parser.add_argument("--query", default="financial risk")
    analyze_parser.add_argument("--limit", type=int, default=25)
    analyze_parser.add_argument("--nlp-mode", choices=sorted(Settings.ALLOWED_NLP_MODES))
    stress_parser = subparsers.add_parser(
        "stress-fixtures", help="analyze fixtures and apply the configured stress trigger"
    )
    stress_parser.add_argument("--query", default="financial risk")
    stress_parser.add_argument("--limit", type=int, default=25)
    stress_parser.add_argument("--nlp-mode", choices=sorted(Settings.ALLOWED_NLP_MODES))
    serve_parser = subparsers.add_parser("serve", help="run the versioned FastAPI service")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8000)
    dashboard_parser = subparsers.add_parser(
        "dashboard", help="run the Streamlit monitoring dashboard"
    )
    dashboard_parser.add_argument("--host", default="127.0.0.1")
    dashboard_parser.add_argument("--port", type=int, default=8501)
    dashboard_parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    return parser


def _run_fixtures(settings: Settings, query: str, limit: int):
    sample_dir = Path(settings.data_dir) / "sample"
    service = IngestionService(
        [
            FixtureAdapter(sample_dir / "gdelt_articles.json"),
            FixtureAdapter(sample_dir / "bluesky_posts.json"),
        ],
        max_text_length=settings.max_text_length,
    )
    return service.run(IngestionRequest(query=query, limit=limit))


def main(argv: Sequence[str] | None = None) -> int:
    """Run a command and return its process exit code."""

    args = build_parser().parse_args(argv)
    settings = Settings.from_env()
    configure_logging(settings.log_level)

    if args.command == "check":
        print(json.dumps(settings.public_summary(), indent=2, sort_keys=True))
        return 0

    if args.command == "serve":
        import uvicorn

        from risk_engine.api.app import create_app

        uvicorn.run(create_app(settings), host=args.host, port=args.port)
        return 0

    if args.command == "dashboard":
        dashboard_app = Path(__file__).parent / "dashboard" / "app.py"
        environment = os.environ.copy()
        environment["RISK_ENGINE_API_URL"] = args.api_url
        command = [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(dashboard_app),
            "--server.address",
            args.host,
            "--server.port",
            str(args.port),
            "--browser.gatherUsageStats",
            "false",
        ]
        return subprocess.run(command, env=environment, check=False).returncode

    if args.command == "ingest-fixtures":
        result = _run_fixtures(settings, args.query, args.limit)
        print(result.model_dump_json(indent=2))
        return 0 if result.failed_source_count == 0 else 1

    if args.command in {"analyze-fixtures", "stress-fixtures"}:
        result = _run_fixtures(settings, args.query, args.limit)
        if result.failed_source_count:
            print(result.model_dump_json(indent=2))
            return 1
        engine = build_risk_engine(settings, mode=args.nlp_mode)
        signals = engine.analyze(result.documents)
        if args.command == "stress-fixtures":
            decisions = build_stress_engine(settings).run_many(signals)
            print(json.dumps([item.model_dump(mode="json") for item in decisions], indent=2))
            return 0
        print(json.dumps([signal.model_dump(mode="json") for signal in signals], indent=2))
        return 0

    raise AssertionError(f"Unhandled command: {args.command}")
