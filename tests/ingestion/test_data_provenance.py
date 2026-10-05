"""Checks that committed synthetic fixtures match the provenance manifest."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit


def test_fixture_checksums_match_source_manifest() -> None:
    manifest = Path("data/sources.yaml").read_text(encoding="utf-8")
    expected = {
        "data/sample/gdelt_articles.json": (
            "297239d5aad5aa96e9d1c7d8edc6c0910fb67a9563af43b88721a47f9c49c4d4"
        ),
        "data/sample/bluesky_posts.json": (
            "867550276a2863ccc204ad6dc7af13f330b6a03a201fb46daff5a08fb1df202c"
        ),
        "data/evaluation/nlp_golden.json": (
            "b54efa00a8c7766f41fda6ea6718dcaf0b0c582bb6bb2f051f9e6d088d4d6f71"
        ),
        "data/replay/banking_stress_news.json": (
            "75fd2c87c0868ae9852b4bef0d2b06d37dda6c9ce3e9bc5d6c70a2519678d13e"
        ),
        "data/replay/banking_stress_social.json": (
            "d1474a86e5e14eaeb95fa7d546d44206661affbd6c0229f18ad9bc705b80f5e5"
        ),
        "data/live-snapshots/2026-10-05-public-metadata.json": (
            "b7970c4e76ffb8bb59997a9190ca20880a28577a6e05aaec8bdae151684738f4"
        ),
        "data/nlp/issuer_watchlist.json": (
            "3317a8118c630e4710080d9d5cdc730055dab134d00626a37ce29cca952a83e6"
        ),
        "data/nlp/event_taxonomy.json": (
            "5bdfdb88f5dd62ba7fe23f0a000f2588648d5a122abc03c9b9b0a83db194d48f"
        ),
        "data/portfolio/portfolio.json": (
            "a95e73f2bff2bcb0c5b7bb13493c8eef5b00fe24dac7d4584f54007b87b530f9"
        ),
        "data/portfolio/scenarios.json": (
            "b90de73bf1bb68644dfcaeac5512bd3f60be97d6541c3ef7da751b011f2de479"
        ),
        "data/portfolio/sector_proxy.json": (
            "d98f842ac30f89fe55e7e5b31504d48b41a57baf453fe68d5db528d6a9258ae7"
        ),
    }

    for filename, checksum in expected.items():
        digest = hashlib.sha256(Path(filename).read_bytes()).hexdigest()
        assert digest == checksum
        assert f"path: {filename}" in manifest
        assert f"sha256: {checksum}" in manifest

    assert len(expected) == 11


def test_replay_bundles_are_synthetic_reserved_domain_records() -> None:
    replay_paths = sorted(Path("data/replay").glob("*.json"))
    payloads = [json.loads(path.read_text(encoding="utf-8")) for path in replay_paths]
    records = [record for payload in payloads for record in payload["records"]]

    assert len(replay_paths) == 2
    assert len(records) == 4
    assert all(payload["synthetic"] is True for payload in payloads)
    assert {payload["source_type"] for payload in payloads} == {"news", "social"}
    assert len({record["source_id"] for record in records}) == 4
    assert all((urlsplit(record["url"]).hostname or "").endswith(".example") for record in records)
    assert all(record["metadata"]["historical_inspiration"] for record in records)
    assert all(
        record["metadata"].get("copied_article_text") is False
        or record["metadata"].get("copied_post_text") is False
        for record in records
    )


def test_live_snapshot_is_metadata_only_and_records_authentication_outcome() -> None:
    snapshot = json.loads(
        Path("data/live-snapshots/2026-10-05-public-metadata.json").read_text(
            encoding="utf-8"
        )
    )

    assert snapshot["classification"] == "public-metadata-only"
    assert snapshot["content_retained"] is False
    assert {source["source"] for source in snapshot["sources"]} == {"gdelt", "bluesky"}
    bluesky = next(source for source in snapshot["sources"] if source["source"] == "bluesky")
    assert bluesky["http_status"] == 403
    assert bluesky["authentication_required"] is True
