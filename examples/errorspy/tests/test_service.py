from __future__ import annotations

import pytest

from app.repository import StorageCampaignRepository
from app.service import CampaignService
from app.storage import FakeStorage
from domain.short_link import ShortLinkSpec
from errors import DomainError, DomainKind


def _service(*, down: bool = False) -> CampaignService:
    return CampaignService(StorageCampaignRepository(FakeStorage(down=down)))


def test_not_found_propagates_unwrapped_through_the_service() -> None:
    with pytest.raises(DomainError) as ei:
        _service().get("missing")
    assert ei.value.kind is DomainKind.NOT_FOUND
    assert ei.value.code == "campaign_missing"


def test_add_link_propagates_domain_not_found_for_missing_campaign() -> None:
    with pytest.raises(DomainError) as ei:
        _service().add_link(
            "missing", ShortLinkSpec(slug="spring-sale", target_url="https://x.com")
        )
    assert ei.value.code == "campaign_missing"
