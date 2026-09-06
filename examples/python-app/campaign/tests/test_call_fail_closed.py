from __future__ import annotations

import pytest
import tesser.testing as ts

import campaign.application as application
import campaign.application.ports as ports
import campaign.client as client
import tesser.errors as errors


@ts.fake
class FakeCampaignIdentity(ports.CampaignIdentity):

    def __init__(self) -> None:
        self.issued = 0

    def issue(
        self, issue_campaign_identity_request: ports.IssueCampaignIdentityRequest
    ) -> ports.IssueCampaignIdentityResponse:
        self.issued += 1
        campaign_id = f"{self.issued:016x}"
        return ports.IssueCampaignIdentityResponse(campaign_id=campaign_id)


@ts.fake
class FakeCampaignRepositoryRecording(ports.CampaignRepository):
    def __init__(self) -> None:
        money_record = ports.MoneyRecord(amount="100.00", currency="USD")
        self._record = ports.CampaignRecord(
            id="0123456789abcdef", budget=money_record, links=()
        )
        self.saved: list[ports.SaveCampaignRequest] = []

    def save(
        self, save_campaign_request: ports.SaveCampaignRequest
    ) -> ports.SaveCampaignResponse:
        self.saved.append(save_campaign_request)
        self._record = ports.CampaignRecord(
            id=save_campaign_request.id, budget=save_campaign_request.budget, links=save_campaign_request.links
        )
        return ports.SaveCampaignResponse()

    def find(
        self, find_campaign_request: ports.FindCampaignRequest
    ) -> ports.FindCampaignResponse:
        if find_campaign_request.campaign_id == self._record.id:
            return ports.FindCampaignResponse(
                outcome=ports.CampaignLookup.FOUND, campaigns=(self._record,)
            )
        return ports.FindCampaignResponse(
            outcome=ports.CampaignLookup.MISSING, campaigns=()
        )

    def find_by_slug(
        self, find_campaign_by_slug_request: ports.FindCampaignBySlugRequest
    ) -> ports.FindCampaignResponse:
        return ports.FindCampaignResponse(
            outcome=ports.CampaignLookup.MISSING, campaigns=()
        )

    def slug_taken(
        self, slug_taken_request: ports.SlugTakenRequest
    ) -> ports.SlugTakenResponse:
        return ports.SlugTakenResponse(
            availability=ports.SlugAvailability.FREE
        )

    def all(
        self, list_campaigns_request: ports.ListCampaignsRequest
    ) -> ports.ListCampaignsResponse:
        return ports.ListCampaignsResponse(campaigns=(self._record,))

    def find_view(
        self, find_campaign_view_request: ports.FindCampaignViewRequest
    ) -> ports.FindCampaignViewResponse:
        row = self._record
        links: list[ports.LinkViewRow] = []
        for link in row.links:
            links.append(ports.LinkViewRow(
                slug=link.slug, target_url=link.target_url, status=link.status
            ))
        campaign_view_row = ports.CampaignViewRow(
            campaign_id=row.id,
            budget_amount=row.budget.amount,
            budget_currency=row.budget.currency,
            links=tuple(links),
        )
        return ports.FindCampaignViewResponse(
            outcome=ports.CampaignViewLookup.FOUND, campaigns=(campaign_view_row,)
        )


@ts.fake
class FakeTargetPolicyBlocking(ports.TargetPolicy):
    def check(self, check_target_request: ports.CheckTargetRequest) -> ports.CheckTargetResponse:
        return ports.CheckTargetResponse(
            verdict=ports.PolicyVerdict.BLOCKED, reason="not on the allow-list"
        )


@ts.fake
class FakeTargetPolicyOutage(ports.TargetPolicy):
    def check(self, check_target_request: ports.CheckTargetRequest) -> ports.CheckTargetResponse:
        raise errors.InfraError("linkpolicy unavailable")


@ts.fake
class FakeTargetPolicyAllowAll(ports.TargetPolicy):
    def check(self, check_target_request: ports.CheckTargetRequest) -> ports.CheckTargetResponse:
        return ports.CheckTargetResponse(verdict=ports.PolicyVerdict.ALLOWED, reason="ok")


def test_rejection_is_a_conflict_and_creates_nothing() -> None:
    fake_campaign_repository_recording = FakeCampaignRepositoryRecording()
    campaign_service = application.CampaignService(fake_campaign_repository_recording, FakeTargetPolicyBlocking(), FakeCampaignIdentity(), fake_campaign_repository_recording)
    add_link_request = client.AddLinkRequest(campaign_id="0123456789abcdef", slug="promo", target_url="https://ok.example/x")
    with pytest.raises(errors.DomainError) as caught:
        campaign_service.add_link(add_link_request)
    assert caught.value.kind is errors.Kind.CONFLICT
    assert fake_campaign_repository_recording.saved == []


def test_outage_propagates_and_creates_nothing() -> None:
    fake_campaign_repository_recording = FakeCampaignRepositoryRecording()
    campaign_service = application.CampaignService(fake_campaign_repository_recording, FakeTargetPolicyOutage(), FakeCampaignIdentity(), fake_campaign_repository_recording)
    add_link_request = client.AddLinkRequest(campaign_id="0123456789abcdef", slug="promo", target_url="https://ok.example/x")
    with pytest.raises(errors.InfraError):
        campaign_service.add_link(add_link_request)
    assert fake_campaign_repository_recording.saved == []


def test_allowed_verdict_creates_the_link() -> None:
    fake_campaign_repository_recording = FakeCampaignRepositoryRecording()
    campaign_service = application.CampaignService(fake_campaign_repository_recording, FakeTargetPolicyAllowAll(), FakeCampaignIdentity(), fake_campaign_repository_recording)
    add_link_request = client.AddLinkRequest(campaign_id="0123456789abcdef", slug="promo", target_url="https://ok.example/x")
    campaign_view = campaign_service.add_link(add_link_request)
    assert [link.slug for link in campaign_view.links] == ["promo"]
    assert len(fake_campaign_repository_recording.saved) == 1
