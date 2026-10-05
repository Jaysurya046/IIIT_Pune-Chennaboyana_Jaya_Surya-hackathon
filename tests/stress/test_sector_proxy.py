from pathlib import Path

from risk_engine.stress.sector_proxy import SectorProxyResolver


def test_sector_proxy_resolves_known_and_unknown_sectors() -> None:
    resolver = SectorProxyResolver(Path("data/portfolio/sector_proxy.json"))

    banking = resolver.resolve("commercial banking")
    unknown = resolver.resolve("Aerospace")

    assert banking is not None
    assert banking.synthetic_sector == "Banking"
    assert banking.label == "illustrative sector proxy"
    assert unknown is None


def test_sector_proxy_resolves_multiple_unique_entities() -> None:
    resolver = SectorProxyResolver(Path("data/portfolio/sector_proxy.json"))

    matches = resolver.resolve_many(("bank", "shipping", "bank", "unknown"))

    assert [match.synthetic_sector for match in matches] == ["Banking", "Transportation"]
    assert all(match.label == "illustrative sector proxy" for match in matches)
