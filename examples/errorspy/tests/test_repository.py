"""Cells B1 (repo not_found), B2 (vendor error translated at the adapter), and
B7 (corrupted record on reconstruction -> infra, not domain validation)."""

from __future__ import annotations

import pytest

from app.repository import StorageCampaignRepository
from app.storage import FakeStorage, StorageError
from domain.campaign import Campaign, CampaignSpec
from domain.short_link import ShortLinkSpec
from domain.values import DateWindowSpec
from errors import DomainError, DomainKind, InfraError

_WINDOW = DateWindowSpec(start="2026-01-01", end="2026-02-01")


def _campaign() -> Campaign:
    return Campaign(
        "c1",
        CampaignSpec(
            window=_WINDOW,
            links=(ShortLinkSpec(slug="spring-sale", target_url="https://x.com"),),
        ),
    )


def test_save_then_get_roundtrip() -> None:
    repo = StorageCampaignRepository(FakeStorage())
    repo.save(_campaign())
    got = repo.get("c1")
    assert got.id == "c1"
    assert str(got.links[0].slug) == "spring-sale"


def test_missing_is_domain_not_found() -> None:
    # B1: a storage miss becomes a domain not_found, never a StorageError.
    repo = StorageCampaignRepository(FakeStorage())
    with pytest.raises(DomainError) as ei:
        repo.get("nope")
    assert ei.value.kind is DomainKind.NOT_FOUND
    assert ei.value.code == "campaign_missing"


def test_outage_is_infra_not_domain() -> None:
    # B2: a storage outage becomes an InfraError (-> 503), not a domain error,
    # and nothing StorageError-shaped escapes.
    repo = StorageCampaignRepository(FakeStorage(down=True))
    with pytest.raises(InfraError) as ei:
        repo.get("c1")
    assert not isinstance(ei.value, DomainError)
    assert not isinstance(ei.value, StorageError)


def test_corrupted_record_is_infra_not_validation() -> None:
    # B7: stored data that fails the domain constructor is corruption, surfaced
    # as infra (-> 500), NOT a domain validation error (the user did not send it).
    storage = FakeStorage()
    storage.put(
        "c1",
        {
            "window": {"start": "2026-01-01", "end": "2026-02-01"},
            "links": [{"slug": "BAD SLUG", "target_url": "https://x.com"}],
        },
    )
    repo = StorageCampaignRepository(storage)
    with pytest.raises(InfraError) as ei:
        repo.get("c1")
    assert not isinstance(ei.value, DomainError)
    # the domain validation error is preserved as the cause, but not surfaced as one
    assert isinstance(ei.value.__cause__, DomainError)
    assert ei.value.__cause__.kind is DomainKind.VALIDATION
