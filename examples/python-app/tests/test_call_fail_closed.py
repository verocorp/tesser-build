from __future__ import annotations

import pytest
import tesser.testing as ts

from campaign.application.parts import (
    CampaignParts,
    PolicyOutcome,
    FoundCampaign,
    MissingCampaign,
    MoneyParts,
)
from campaign.application.service import CampaignRepository, CampaignService, TargetPolicy
from campaign.client.client import AddLinkRequest
from errors import DomainError, InfraError, Kind


@ts.fake
class FakeCampaignRepositoryRecording(CampaignRepository):
    def __init__(self) -> None:
        budget = MoneyParts(amount="100.00", currency="USD")
        self._parts = CampaignParts(id="0123456789abcdef", budget=budget, links=())
        self.saved: list[CampaignParts] = []

    def save(self, parts: CampaignParts) -> None:
        self.saved.append(parts)

    def find(self, id: str) -> FoundCampaign | MissingCampaign:
        return FoundCampaign(parts=self._parts) if id == self._parts.id else MissingCampaign()

    def find_by_slug(self, slug: str) -> FoundCampaign | MissingCampaign:
        return MissingCampaign()

    def slug_taken(self, slug: str) -> bool:
        return False

    def all(self) -> tuple[CampaignParts, ...]:
        return (self._parts,)


@ts.fake
class FakeTargetPolicyBlocking(TargetPolicy):
    def check(self, target_url: str) -> PolicyOutcome:
        return PolicyOutcome(False, "not on the allow-list")


@ts.fake
class FakeTargetPolicyOutage(TargetPolicy):
    def check(self, target_url: str) -> PolicyOutcome:
        raise InfraError("linkpolicy unavailable")


@ts.fake
class FakeTargetPolicyAllowAll(TargetPolicy):
    def check(self, target_url: str) -> PolicyOutcome:
        return PolicyOutcome(True, "ok")


def test_rejection_is_a_conflict_and_creates_nothing() -> None:
    repo = FakeCampaignRepositoryRecording()
    svc = CampaignService(repo, FakeTargetPolicyBlocking())
    req = AddLinkRequest(campaign_id="0123456789abcdef", slug="promo", target_url="https://ok.example/x")
    with pytest.raises(DomainError) as caught:
        svc.add_link(req)
    assert caught.value.kind is Kind.CONFLICT
    assert repo.saved == []


def test_outage_propagates_and_creates_nothing() -> None:
    repo = FakeCampaignRepositoryRecording()
    svc = CampaignService(repo, FakeTargetPolicyOutage())
    req = AddLinkRequest(campaign_id="0123456789abcdef", slug="promo", target_url="https://ok.example/x")
    with pytest.raises(InfraError):
        svc.add_link(req)
    assert repo.saved == []


def test_allowed_verdict_creates_the_link() -> None:
    repo = FakeCampaignRepositoryRecording()
    svc = CampaignService(repo, FakeTargetPolicyAllowAll())
    req = AddLinkRequest(campaign_id="0123456789abcdef", slug="promo", target_url="https://ok.example/x")
    view = svc.add_link(req)
    assert [link.slug for link in view.links] == ["promo"]
    assert len(repo.saved) == 1
