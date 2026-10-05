"""Command-line diagnostics for the project scaffold."""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
from collections.abc import Sequence
from pathlib import Path

import httpx

from risk_engine import __version__
from risk_engine.api.models import IngestionRunRequest, SourceMode
from risk_engine.api.service import RiskApplicationService
from risk_engine.benchmarking import BenchmarkDataError, run_benchmark
from risk_engine.config import Settings
from risk_engine.ingestion.adapters import FixtureAdapter
from risk_engine.ingestion.models import IngestionRequest
from risk_engine.ingestion.service import IngestionService
from risk_engine.logging_config import configure_logging
from risk_engine.nlp.factory import build_risk_engine, synthetic_batch_as_of
from risk_engine.nlp.sentiment import ModelDependencyError
from risk_engine.persistence import SQLiteStore
from risk_engine.stress.factory import build_stress_engine


class DemoCommandError(RuntimeError):
    """Raised when the local demo cannot start exactly as requested."""


def _positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be greater than zero")
    return parsed


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
    replay_parser = subparsers.add_parser(
        "replay", help="run the deterministic synthetic banking-stress replay"
    )
    replay_parser.add_argument("--query", default="banking stress")
    replay_parser.add_argument("--limit", type=int, default=25)
    serve_parser = subparsers.add_parser("serve", help="run the versioned FastAPI service")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8000)
    serve_parser.add_argument(
        "--warm-models",
        action="store_true",
        help="load pinned model-mode components before accepting API requests",
    )
    serve_parser.add_argument(
        "--auto-stress",
        action="store_true",
        help="persist stress decisions for newly analyzed signals above the trigger",
    )
    serve_parser.add_argument(
        "--poll-minutes",
        type=_positive_float,
        help="enable bounded polling at this interval; requires --source-mode",
    )
    serve_parser.add_argument(
        "--source-mode",
        choices=tuple(mode.value for mode in SourceMode),
        help="explicit source mode for polling",
    )
    serve_parser.add_argument("--query", default="financial risk")
    serve_parser.add_argument("--nlp-mode", choices=sorted(Settings.ALLOWED_NLP_MODES))
    dashboard_parser = subparsers.add_parser(
        "dashboard", help="run the Streamlit monitoring dashboard"
    )
    dashboard_parser.add_argument("--host", default="127.0.0.1")
    dashboard_parser.add_argument("--port", type=int, default=8501)
    dashboard_parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    demo_parser = subparsers.add_parser(
        "demo", help="seed data and run the local API plus dashboard"
    )
    demo_parser.add_argument(
        "--source-mode",
        choices=(SourceMode.FIXTURES.value, SourceMode.REPLAY.value),
        default=SourceMode.REPLAY.value,
    )
    demo_parser.add_argument(
        "--nlp-mode",
        choices=sorted(Settings.ALLOWED_NLP_MODES),
        default="deterministic",
    )
    demo_parser.add_argument("--host", default="127.0.0.1")
    demo_parser.add_argument("--api-port", type=int, default=8000)
    demo_parser.add_argument("--dashboard-port", type=int, default=8501)
    demo_parser.add_argument(
        "--open-browser",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="open the Streamlit UI in a browser (use --no-open-browser for headless use)",
    )
    validation_parser = subparsers.add_parser(
        "validate", help="run the reproducible offline validation benchmark"
    )
    validation_parser.add_argument("--max-seconds", type=float, default=5.0)
    validation_parser.add_argument("--output", type=Path)
    benchmark_parser = subparsers.add_parser(
        "benchmark", help="compare deterministic and model sentiment on an external CSV"
    )
    benchmark_parser.add_argument("--dataset", type=Path, required=True)
    benchmark_parser.add_argument("--text-col", required=True)
    benchmark_parser.add_argument("--label-col", required=True)
    benchmark_parser.add_argument("--output", type=Path)
    benchmark_parser.add_argument("--markdown-output", type=Path)
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


def _run_replay(settings: Settings, query: str, limit: int):
    replay_dir = Path(settings.data_dir) / "replay"
    service = IngestionService(
        [
            FixtureAdapter(replay_dir / "banking_stress_news.json"),
            FixtureAdapter(replay_dir / "banking_stress_social.json"),
        ],
        max_text_length=settings.max_text_length,
    )
    return service.run(IngestionRequest(query=query, limit=limit))


def _assert_demo_port_available(host: str, port: int, label: str) -> None:
    if not 1 <= port <= 65_535:
        raise DemoCommandError(f"{label} port must be between 1 and 65535")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as candidate:
            candidate.bind((host, port))
    except OSError as error:
        raise DemoCommandError(f"{label} port {host}:{port} is unavailable") from error


def _seed_demo(settings: Settings, source_mode: SourceMode, nlp_mode: str) -> tuple[int, int]:
    store = SQLiteStore(settings.database_url)
    try:
        service = RiskApplicationService(settings, store)
        query = "banking stress" if source_mode is SourceMode.REPLAY else "portfolio risk"
        ingestion = service.ingest(
            IngestionRunRequest(query=query, source_mode=source_mode)
        )
        if ingestion.failed_source_count:
            raise DemoCommandError(
                f"{source_mode.value} ingestion failed for "
                f"{ingestion.failed_source_count} source(s)"
            )
        analysis = service.analyze(ingestion.run_id, nlp_mode)
        if analysis is None:  # pragma: no cover - the saved run must be retrievable
            raise DemoCommandError("seeded ingestion run could not be analyzed")
        return ingestion.document_count, analysis.signal_count
    finally:
        store.close()


def _demo_client_host(host: str) -> str:
    if host == "0.0.0.0":
        return "127.0.0.1"
    if host == "::":
        return "::1"
    return host


def _wait_for_demo_api(
    process: subprocess.Popen,
    health_url: str,
    *,
    timeout_seconds: float = 20.0,
) -> None:
    deadline = time.monotonic() + timeout_seconds
    with httpx.Client(timeout=0.5) as client:
        while time.monotonic() < deadline:
            return_code = process.poll()
            if return_code is not None:
                raise DemoCommandError(
                    f"API process exited before readiness with code {return_code}"
                )
            try:
                response = client.get(health_url)
                if response.status_code == 200:
                    return
            except httpx.HTTPError:
                pass
            time.sleep(0.1)
    raise DemoCommandError(f"API did not become healthy within {timeout_seconds:.0f} seconds")


def _stop_demo_api(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def _run_demo(settings: Settings, args: argparse.Namespace) -> int:
    if args.api_port == args.dashboard_port:
        raise DemoCommandError("API and dashboard ports must be different")
    _assert_demo_port_available(args.host, args.api_port, "API")
    _assert_demo_port_available(args.host, args.dashboard_port, "dashboard")

    source_mode = SourceMode(args.source_mode)
    document_count, signal_count = _seed_demo(settings, source_mode, args.nlp_mode)
    print(
        f"Seeded {document_count} {source_mode.value} documents and "
        f"persisted {signal_count} {args.nlp_mode} signals."
    )

    api_command = [
        sys.executable,
        "-m",
        "risk_engine",
        "serve",
        "--host",
        args.host,
        "--port",
        str(args.api_port),
    ]
    client_host = _demo_client_host(args.host)
    api_url = f"http://{client_host}:{args.api_port}"
    api_process = subprocess.Popen(api_command, env=os.environ.copy())
    try:
        _wait_for_demo_api(api_process, f"{api_url}/health")
        dashboard_app = Path(__file__).parent / "dashboard" / "app.py"
        environment = os.environ.copy()
        environment["RISK_ENGINE_API_URL"] = api_url
        dashboard_command = [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(dashboard_app),
            "--server.address",
            args.host,
            "--server.port",
            str(args.dashboard_port),
            "--server.headless",
            str(not args.open_browser).lower(),
            "--browser.gatherUsageStats",
            "false",
        ]
        return subprocess.run(
            dashboard_command,
            env=environment,
            check=False,
        ).returncode
    finally:
        _stop_demo_api(api_process)


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

        if args.poll_minutes is not None and args.source_mode is None:
            print(
                json.dumps(
                    {
                        "classification": "polling-error",
                        "message": "--source-mode is required with --poll-minutes",
                    }
                ),
                file=sys.stderr,
            )
            return 1
        if (
            args.poll_minutes is not None
            and args.source_mode == SourceMode.LIVE.value
            and settings.offline_mode
        ):
            print(
                json.dumps(
                    {
                        "classification": "polling-error",
                        "message": "live polling requires RISK_ENGINE_OFFLINE_MODE=false",
                    }
                ),
                file=sys.stderr,
            )
            return 1

        app_options: dict[str, object] = {"warm_model_mode": args.warm_models}
        if args.auto_stress:
            app_options["auto_stress"] = True
        if args.poll_minutes is not None:
            app_options.update(
                poll_minutes=args.poll_minutes,
                poll_source_mode=args.source_mode,
                poll_query=args.query,
                poll_nlp_mode=args.nlp_mode,
            )
        uvicorn.run(
            create_app(settings, **app_options),
            host=args.host,
            port=args.port,
        )
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

    if args.command == "demo":
        try:
            return _run_demo(settings, args)
        except (DemoCommandError, ModelDependencyError, OSError) as error:
            print(
                json.dumps(
                    {
                        "classification": "demo-error",
                        "error_type": type(error).__name__,
                        "message": str(error),
                    }
                ),
                file=sys.stderr,
            )
            return 1

    if args.command == "validate":
        from risk_engine.validation import run_validation

        report = run_validation(data_dir=settings.data_dir, max_seconds=args.max_seconds)
        payload = report.model_dump_json(indent=2)
        if args.output is not None:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(f"{payload}\n", encoding="utf-8")
        print(payload)
        return 0 if report.passed else 1

    if args.command == "benchmark":
        try:
            report = run_benchmark(
                args.dataset,
                text_column=args.text_col,
                label_column=args.label_col,
                settings=settings,
            )
        except (BenchmarkDataError, ModelDependencyError, OSError) as error:
            print(
                json.dumps(
                    {
                        "classification": "benchmark-error",
                        "error_type": type(error).__name__,
                        "message": str(error),
                    }
                ),
                file=sys.stderr,
            )
            return 1
        payload = report.model_dump_json(indent=2)
        if args.output is not None:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(f"{payload}\n", encoding="utf-8")
        if args.markdown_output is not None:
            args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
            args.markdown_output.write_text(f"{report.to_markdown()}\n", encoding="utf-8")
        print(payload)
        return 0

    if args.command == "ingest-fixtures":
        result = _run_fixtures(settings, args.query, args.limit)
        print(result.model_dump_json(indent=2))
        return 0 if result.failed_source_count == 0 else 1

    if args.command == "replay":
        result = _run_replay(settings, args.query, args.limit)
        if result.failed_source_count:
            print(result.model_dump_json(indent=2))
            return 1
        signals = build_risk_engine(settings, mode="deterministic").analyze(
            result.documents,
            as_of=synthetic_batch_as_of(result.documents),
        )
        decisions = build_stress_engine(settings).run_many(signals)
        print(
            json.dumps(
                {
                    "classification": "synthetic-replay",
                    "signals": [item.model_dump(mode="json") for item in signals],
                    "decisions": [item.model_dump(mode="json") for item in decisions],
                },
                indent=2,
            )
        )
        return 0

    if args.command in {"analyze-fixtures", "stress-fixtures"}:
        result = _run_fixtures(settings, args.query, args.limit)
        if result.failed_source_count:
            print(result.model_dump_json(indent=2))
            return 1
        engine = build_risk_engine(settings, mode=args.nlp_mode)
        signals = engine.analyze(
            result.documents,
            as_of=synthetic_batch_as_of(result.documents),
        )
        if args.command == "stress-fixtures":
            decisions = build_stress_engine(settings).run_many(signals)
            print(json.dumps([item.model_dump(mode="json") for item in decisions], indent=2))
            return 0
        print(json.dumps([signal.model_dump(mode="json") for signal in signals], indent=2))
        return 0

    raise AssertionError(f"Unhandled command: {args.command}")
