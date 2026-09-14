from __future__ import annotations

import pytest
import tesser.testing as ts

import campaign.application as application
import campaign.application.ports as ports
import campaign.client as client


@ts.fake
class FakeCampaignIdentity(ports.CampaignIdentity):

    def __init__(self) -> None:
        self.issued = 0

    def issue_campaign_identity(
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

    def save_campaign(
        self, save_campaign_request: ports.SaveCampaignRequest
    ) -> ports.SaveCampaignResponse:
        self.saved.append(save_campaign_request)
        self._record = ports.CampaignRecord(
            id=save_campaign_request.id, budget=save_campaign_request.budget, links=save_campaign_request.links
        )
        return ports.SaveCampaignResponse()

    def load_campaign(
        self, load_campaign_request: ports.LoadCampaignRequest
    ) -> ports.LoadCampaignResponse:
        if load_campaign_request.campaign_id == self._record.id:
            return ports.LoadCampaignResponse(
                outcome=ports.LoadCampaignOutcome.FOUND, campaigns=(self._record,)
            )
        return ports.LoadCampaignResponse(
            outcome=ports.LoadCampaignOutcome.NOT_FOUND, campaigns=()
        )

    def load_campaign_by_slug(
        self, load_campaign_by_slug_request: ports.LoadCampaignBySlugRequest
    ) -> ports.LoadCampaignBySlugResponse:
        return ports.LoadCampaignBySlugResponse(
            outcome=ports.LoadCampaignBySlugOutcome.NOT_FOUND, campaigns=()
        )

    def slug_taken(
        self, slug_taken_request: ports.SlugTakenRequest
    ) -> ports.SlugTakenResponse:
        return ports.SlugTakenResponse(
            availability=ports.SlugAvailability.FREE
        )

    def list_campaigns(
        self, list_campaigns_request: ports.ListCampaignsRequest
    ) -> ports.ListCampaignsResponse:
        return ports.ListCampaignsResponse(campaigns=(self._record,))

    def find_campaign(
        self, find_campaign_request: ports.FindCampaignRequest
    ) -> ports.FindCampaignResponse:
        row = self._record
        links: list[ports.Link] = []
        for link in row.links:
            links.append(ports.Link(
                slug=link.slug, target_url=link.target_url, status=link.status
            ))
        campaign = ports.Campaign(
            campaign_id=row.id,
            budget_amount=row.budget.amount,
            budget_currency=row.budget.currency,
            links=tuple(links),
        )
        return ports.FindCampaignResponse(
            outcome=ports.FindCampaignOutcome.FOUND, campaigns=(campaign,)
        )


@ts.fake
class FakeTargetPolicyBlocking(ports.TargetPolicy):
    def check_target(self, check_target_request: ports.CheckTargetRequest) -> ports.CheckTargetResponse:
        return ports.CheckTargetResponse(
            outcome=ports.CheckTargetOutcome.BLOCKED, reason="not on the allow-list"
        )


@ts.fake
class FakeTargetPolicyOutage(ports.TargetPolicy):
    def check_target(self, check_target_request: ports.CheckTargetRequest) -> ports.CheckTargetResponse:
        raise ports.PolicyUnavailable("linkpolicy unavailable")


@ts.fake
class FakeTargetPolicyAllowAll(ports.TargetPolicy):
    def check_target(self, check_target_request: ports.CheckTargetRequest) -> ports.CheckTargetResponse:
        return ports.CheckTargetResponse(outcome=ports.CheckTargetOutcome.ALLOWED, reason="ok")


def test_rejection_is_a_conflict_and_creates_nothing() -> None:
    fake_campaign_repository_recording = FakeCampaignRepositoryRecording()
    campaign_service = application.CampaignService(fake_campaign_repository_recording, FakeTargetPolicyBlocking(), FakeCampaignIdentity(), fake_campaign_repository_recording)
    add_link_request = client.AddLinkRequest(campaign_id="0123456789abcdef", slug="promo", target_url="https://ok.example/x")
    with pytest.raises(client.Conflict) as caught:
        campaign_service.add_link(add_link_request)
    assert caught.value.code == "destination_blocked"
    assert fake_campaign_repository_recording.saved == []


def test_outage_is_the_contexts_unavailable_and_creates_nothing() -> None:
    fake_campaign_repository_recording = FakeCampaignRepositoryRecording()
    campaign_service = application.CampaignService(fake_campaign_repository_recording, FakeTargetPolicyOutage(), FakeCampaignIdentity(), fake_campaign_repository_recording)
    add_link_request = client.AddLinkRequest(campaign_id="0123456789abcdef", slug="promo", target_url="https://ok.example/x")
    with pytest.raises(client.Unavailable) as caught:
        campaign_service.add_link(add_link_request)
    assert isinstance(caught.value.__cause__, ports.PolicyUnavailable)
    assert fake_campaign_repository_recording.saved == []


def test_allowed_verdict_creates_the_link() -> None:
    fake_campaign_repository_recording = FakeCampaignRepositoryRecording()
    campaign_service = application.CampaignService(fake_campaign_repository_recording, FakeTargetPolicyAllowAll(), FakeCampaignIdentity(), fake_campaign_repository_recording)
    add_link_request = client.AddLinkRequest(campaign_id="0123456789abcdef", slug="promo", target_url="https://ok.example/x")
    add_link_response = campaign_service.add_link(add_link_request)
    assert [link.slug for link in add_link_response.campaign.links] == ["promo"]
    assert len(fake_campaign_repository_recording.saved) == 1
