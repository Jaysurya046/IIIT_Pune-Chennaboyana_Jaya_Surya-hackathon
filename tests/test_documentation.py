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


def test_required_phase_eight_artifacts_exist() -> None:
    required = (
        "docs/architecture.png",
        "docs/assets/architecture.svg",
        "docs/implementation-guide.md",
        "docs/dataset-guide.md",
        "docs/results.md",
        "docs/demo-script.md",
    )

    for relative_path in required:
        path = ROOT / relative_path
        assert path.is_file(), f"missing Phase 8 artifact: {relative_path}"
        assert path.stat().st_size > 0, f"empty Phase 8 artifact: {relative_path}"


def test_architecture_png_is_high_resolution() -> None:
    path = ROOT / "docs" / "architecture.png"
    with path.open("rb") as image:
        header = image.read(24)

    assert header[:8] == b"\x89PNG\r\n\x1a\n"
    width, height = struct.unpack(">II", header[16:24])
    assert width >= 1600
    assert height >= 900


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


def test_demo_runbook_covers_both_time_limits_and_data_disclosure() -> None:
    content = (ROOT / "docs" / "demo-script.md").read_text(encoding="utf-8")

    assert "Five-Minute Functional Demonstration" in content
    assert "Up-to-Ten-Minute Recorded Walkthrough" in content
    assert "synthetic" in content.lower()
    assert "incognito" in content.lower()
