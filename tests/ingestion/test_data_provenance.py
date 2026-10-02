"""Checks that committed synthetic fixtures match the provenance manifest."""

from __future__ import annotations

import hashlib
from pathlib import Path


def test_fixture_checksums_match_source_manifest() -> None:
    manifest = Path("data/sources.yaml").read_text(encoding="utf-8")
    expected = {
        "data/sample/gdelt_articles.json": (
            "297239d5aad5aa96e9d1c7d8edc6c0910fb67a9563af43b88721a47f9c49c4d4"
        ),
        "data/sample/bluesky_posts.json": (
            "867550276a2863ccc204ad6dc7af13f330b6a03a201fb46daff5a08fb1df202c"
        ),
    }

    for filename, checksum in expected.items():
        digest = hashlib.sha256(Path(filename).read_bytes()).hexdigest()
        assert digest == checksum
        assert f"path: {filename}" in manifest
        assert f"sha256: {checksum}" in manifest
