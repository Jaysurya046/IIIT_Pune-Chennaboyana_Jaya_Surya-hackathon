from __future__ import annotations

import re
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"


def test_submission_readme_contains_required_sections_and_links() -> None:
    content = README.read_text(encoding="utf-8")

    for heading in (
        "## 1. Project Overview / Problem Statement & Approach",
        "## 2. Architecture & Tech Stack",
        "## 3. Dataset Used",
        "## 4. Quickstart & Installation",
        "## 5. Key Results & Domain Impact",
    ):
        assert heading in content

    assert "docs/architecture.png" in content
    assert "docs/dataset-guide.md" in content
    assert "docs/demo-script.md" in content
    assert "git clone https://github.com/Jaysurya046/" in content
    assert "python -m risk_engine dashboard" in content


def test_required_submission_artifacts_exist() -> None:
    required = (
        "docs/architecture.png",
        "docs/assets/architecture.svg",
        "docs/implementation-guide.md",
        "docs/dataset-guide.md",
        "docs/results.md",
        "docs/demo-script.md",
        "docs/presentation.pdf",
    )

    for relative_path in required:
        path = ROOT / relative_path
        assert path.is_file(), f"missing required artifact: {relative_path}"
        assert path.stat().st_size > 0, f"empty required artifact: {relative_path}"


def test_architecture_png_is_high_resolution() -> None:
    path = ROOT / "docs" / "architecture.png"
    with path.open("rb") as image:
        header = image.read(24)

    assert header[:8] == b"\x89PNG\r\n\x1a\n"
    width, height = struct.unpack(">II", header[16:24])
    assert width >= 1600
    assert height >= 900


def test_dashboard_evidence_screenshots_are_committed_and_reviewable() -> None:
    screenshots = (
        "source-health.png",
        "risk-signal-timeline.png",
        "organic-stress-result.png",
        "hypothetical-what-if.png",
    )
    readme = README.read_text(encoding="utf-8")

    for filename in screenshots:
        path = ROOT / "docs" / "img" / filename
        assert path.is_file(), f"missing dashboard evidence screenshot: {filename}"
        assert path.stat().st_size >= 50_000, (
            f"dashboard screenshot is unexpectedly small: {filename}"
        )
        with path.open("rb") as image:
            header = image.read(24)
        assert header[:8] == b"\x89PNG\r\n\x1a\n"
        width, height = struct.unpack(">II", header[16:24])
        assert (width, height) == (1440, 1000)
        assert f"docs/img/{filename}" in readme


def test_local_markdown_links_resolve() -> None:
    markdown_files = [README, *sorted((ROOT / "docs").glob("*.md"))]
    link_pattern = re.compile(r"!?\[[^]]*]\(([^)]+)\)")

    missing: list[str] = []
    for markdown_path in markdown_files:
        content = markdown_path.read_text(encoding="utf-8")
        for raw_target in link_pattern.findall(content):
            target = raw_target.strip().strip("<>").split("#", maxsplit=1)[0]
            if not target or "://" in target or target.startswith("mailto:"):
                continue
            resolved = (markdown_path.parent / target).resolve()
            if not resolved.exists():
                missing.append(f"{markdown_path.relative_to(ROOT)} -> {target}")

    assert missing == []


def test_dataset_guide_preserves_source_classification_and_caveats() -> None:
    guide = (ROOT / "docs" / "dataset-guide.md").read_text(encoding="utf-8")
    manifest = (ROOT / "data" / "sources.yaml").read_text(encoding="utf-8")

    assert "GDELT DOC API" in guide
    assert "Bluesky Public AppView" in guide
    assert "synthetic" in guide.lower()
    assert "not an estimate" in guide
    assert len(re.findall(r"sha256: [0-9a-f]{64}", manifest)) == 9


def test_external_benchmark_documents_source_license_and_claim_boundary() -> None:
    benchmark = (ROOT / "docs" / "benchmark.md").read_text(encoding="utf-8")

    assert "Financial PhraseBank v1.0" in benchmark
    assert "598b6aad98f7c8d67be161b12a4b5f2497e07edd" in benchmark
    assert "CC BY-NC-SA 3.0" in benchmark
    assert "a7a3128b1380b32d27f28b29c5f57c662492fd6ae6293a778d02593ef5bedae1" in benchmark
    assert "not an out-of-sample generalization estimate" in benchmark
    assert "0/2264" in benchmark
    assert "no ground-truth trigger-quality metric" not in benchmark
    assert "not a labelled trigger-quality metric" in benchmark


def test_demo_runbook_covers_both_time_limits_and_data_disclosure() -> None:
    content = (ROOT / "docs" / "demo-script.md").read_text(encoding="utf-8")

    assert "Five-Minute Functional Demonstration" in content
    assert "Up-to-Ten-Minute Recorded Walkthrough" in content
    assert "synthetic" in content.lower()
    assert "incognito" in content.lower()


def test_directional_and_derivative_assumptions_are_explicit() -> None:
    architecture = (ROOT / "docs" / "architecture.md").read_text(encoding="utf-8")
    dashboard = (ROOT / "docs" / "dashboard.md").read_text(encoding="utf-8")
    data_guide = (ROOT / "data" / "README.md").read_text(encoding="utf-8")
    readme = README.read_text(encoding="utf-8")

    for content in (architecture, dashboard, readme):
        normalized = " ".join(content.split())
        assert "direction-agnostic" in normalized
        assert "positive sentiment is harmful" in normalized

    for content in (architecture, dashboard, data_guide, readme):
        normalized = " ".join(content.split())
        assert "`rate_shock_bps`" in normalized and "means rates rise" in normalized
        assert "DV01" in normalized and "USD" in normalized and "+1 bp" in normalized
        assert "delta_exposure" in normalized
        assert "underlying_shock" in normalized


def test_presentation_pdf_is_real_and_has_submission_page_count() -> None:
    presentation = ROOT / "docs" / "presentation.pdf"
    payload = presentation.read_bytes()

    assert payload.startswith(b"%PDF-")
    assert len(payload) >= 100_000
    page_count = len(re.findall(rb"/Type\s*/Page\b", payload))
    assert 5 <= page_count <= 7


def test_readme_results_are_one_evidence_table_plus_screenshots() -> None:
    readme = README.read_text(encoding="utf-8")
    results = readme.split("## 5. Key Results & Domain Impact", maxsplit=1)[1].split(
        "## Reviewer Guide", maxsplit=1
    )[0]

    assert len(re.findall(r"^\|---", results, flags=re.MULTILINE)) == 1
    assert "docs/benchmark.md" in results
    assert "docs/results.md" in results
    for filename in (
        "risk-signal-timeline.png",
        "source-health.png",
        "organic-stress-result.png",
        "hypothetical-what-if.png",
    ):
        assert f"docs/img/{filename}" in results


def test_release_docs_use_current_progress_path_and_ci_matrix() -> None:
    readme = README.read_text(encoding="utf-8")
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert (ROOT / "docs" / "progress.md").is_file()
    assert not (ROOT / "progress.md").exists()
    assert "docs/progress.md" in readme
    assert "python-version: [\"3.11\", \"3.13\"]" in workflow
    assert "HF_HUB_OFFLINE" in workflow
    assert "TRANSFORMERS_OFFLINE" in workflow
    assert "deferred" not in readme.lower()
