from __future__ import annotations

import pytest
import tesser.testing as ts

import campaign.application.parts as parts
import campaign.application.service as service
import campaign.client.client as client
from errors import DomainError, InfraError, Kind


@ts.fake
class FakeCampaignRepositoryRecording(service.CampaignRepository):
    def __init__(self) -> None:
        budget = parts.MoneyParts(amount="100.00", currency="USD")
        self._parts = parts.CampaignParts(id="0123456789abcdef", budget=budget, links=())
        self.saved: list[parts.CampaignParts] = []

    def save(self, parts: parts.CampaignParts) -> None:
        self.saved.append(parts)

    def find(self, id: str) -> parts.FoundCampaign | parts.MissingCampaign:
        return parts.FoundCampaign(parts=self._parts) if id == self._parts.id else parts.MissingCampaign()

    def find_by_slug(self, slug: str) -> parts.FoundCampaign | parts.MissingCampaign:
        return parts.MissingCampaign()

    def slug_taken(self, slug: str) -> bool:
        return False

    def all(self) -> tuple[parts.CampaignParts, ...]:
        return (self._parts,)


@ts.fake
class FakeTargetPolicyBlocking(service.TargetPolicy):
    def check(self, target_url: str) -> parts.PolicyOutcome:
        return parts.PolicyOutcome(False, "not on the allow-list")


@ts.fake
class FakeTargetPolicyOutage(service.TargetPolicy):
    def check(self, target_url: str) -> parts.PolicyOutcome:
        raise InfraError("linkpolicy unavailable")


@ts.fake
class FakeTargetPolicyAllowAll(service.TargetPolicy):
    def check(self, target_url: str) -> parts.PolicyOutcome:
        return parts.PolicyOutcome(True, "ok")


def test_rejection_is_a_conflict_and_creates_nothing() -> None:
    repo = FakeCampaignRepositoryRecording()
    svc = service.CampaignService(repo, FakeTargetPolicyBlocking())
    req = client.AddLinkRequest(campaign_id="0123456789abcdef", slug="promo", target_url="https://ok.example/x")
    with pytest.raises(DomainError) as caught:
        svc.add_link(req)
    assert caught.value.kind is Kind.CONFLICT
    assert repo.saved == []


def test_outage_propagates_and_creates_nothing() -> None:
    repo = FakeCampaignRepositoryRecording()
    svc = service.CampaignService(repo, FakeTargetPolicyOutage())
    req = client.AddLinkRequest(campaign_id="0123456789abcdef", slug="promo", target_url="https://ok.example/x")
    with pytest.raises(InfraError):
        svc.add_link(req)
    assert repo.saved == []


def test_allowed_verdict_creates_the_link() -> None:
    repo = FakeCampaignRepositoryRecording()
    svc = service.CampaignService(repo, FakeTargetPolicyAllowAll())
    req = client.AddLinkRequest(campaign_id="0123456789abcdef", slug="promo", target_url="https://ok.example/x")
    view = svc.add_link(req)
    assert [link.slug for link in view.links] == ["promo"]
    assert len(repo.saved) == 1
