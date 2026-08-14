from __future__ import annotations

import pytest
import tesser.testing as ts

import campaign.application.ports.campaign_repository as campaign_repository
import campaign.application.ports.target_policy as target_policy
import campaign.application.service as service
import campaign.client.client as client
from errors import DomainError, InfraError, Kind


@ts.fake
class FakeCampaignRepositoryRecording(campaign_repository.CampaignRepository):
    def __init__(self) -> None:
        budget = campaign_repository.MoneyRecord(amount="100.00", currency="USD")
        self._record = campaign_repository.CampaignRecord(
            id="0123456789abcdef", budget=budget, links=()
        )
        self.saved: list[campaign_repository.SaveCampaignRequest] = []

    def save(
        self, request: campaign_repository.SaveCampaignRequest
    ) -> campaign_repository.SaveCampaignResponse:
        self.saved.append(request)
        return campaign_repository.SaveCampaignResponse()

    def find(
        self, request: campaign_repository.FindCampaignRequest
    ) -> campaign_repository.FindCampaignResponse:
        if request.campaign_id == self._record.id:
            return campaign_repository.FindCampaignResponse(
                outcome=campaign_repository.CampaignLookup.FOUND, campaigns=(self._record,)
            )
        return campaign_repository.FindCampaignResponse(
            outcome=campaign_repository.CampaignLookup.MISSING, campaigns=()
        )

    def find_by_slug(
        self, request: campaign_repository.FindCampaignBySlugRequest
    ) -> campaign_repository.FindCampaignResponse:
        return campaign_repository.FindCampaignResponse(
            outcome=campaign_repository.CampaignLookup.MISSING, campaigns=()
        )

    def slug_taken(
        self, request: campaign_repository.SlugTakenRequest
    ) -> campaign_repository.SlugTakenResponse:
        return campaign_repository.SlugTakenResponse(
            availability=campaign_repository.SlugAvailability.FREE
        )

    def all(
        self, request: campaign_repository.ListCampaignsRequest
    ) -> campaign_repository.ListCampaignsResponse:
        return campaign_repository.ListCampaignsResponse(campaigns=(self._record,))


@ts.fake
class FakeTargetPolicyBlocking(target_policy.TargetPolicy):
    def check(self, request: target_policy.CheckTargetRequest) -> target_policy.CheckTargetResponse:
        return target_policy.CheckTargetResponse(
            verdict=target_policy.PolicyVerdict.BLOCKED, reason="not on the allow-list"
        )


@ts.fake
class FakeTargetPolicyOutage(target_policy.TargetPolicy):
    def check(self, request: target_policy.CheckTargetRequest) -> target_policy.CheckTargetResponse:
        raise InfraError("linkpolicy unavailable")


@ts.fake
class FakeTargetPolicyAllowAll(target_policy.TargetPolicy):
    def check(self, request: target_policy.CheckTargetRequest) -> target_policy.CheckTargetResponse:
        return target_policy.CheckTargetResponse(verdict=target_policy.PolicyVerdict.ALLOWED, reason="ok")


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
