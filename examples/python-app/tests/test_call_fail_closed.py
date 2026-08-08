from __future__ import annotations

import pytest
import tesser.testing as ts

from campaign.application.parts import (
    CampaignParts,
    CheckOutcome,
    FoundCampaign,
    MissingCampaign,
    MoneyParts,
)
from campaign.application.service import CampaignRepository, CampaignService, TargetChecker
from campaign.client.client import AddLinkRequest
from errors import DomainError, InfraError, Kind


@ts.fake
class _RecordingRepo(CampaignRepository):
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
class _Blocking(TargetChecker):
    def check(self, target_url: str) -> CheckOutcome:
        return CheckOutcome(False, "not on the allow-list")


@ts.fake
class _Outage(TargetChecker):
    def check(self, target_url: str) -> CheckOutcome:
        raise InfraError("linkpolicy unavailable")


@ts.fake
class _AllowAll(TargetChecker):
    def check(self, target_url: str) -> CheckOutcome:
        return CheckOutcome(True, "ok")


def test_rejection_is_a_conflict_and_creates_nothing() -> None:
    repo = _RecordingRepo()
    svc = CampaignService(repo, _Blocking())
    req = AddLinkRequest(campaign_id="0123456789abcdef", slug="promo", target_url="https://ok.example/x")
    with pytest.raises(DomainError) as caught:
        svc.add_link(req)
    assert caught.value.kind is Kind.CONFLICT
    assert repo.saved == []


def test_outage_propagates_and_creates_nothing() -> None:
    repo = _RecordingRepo()
    svc = CampaignService(repo, _Outage())
    req = AddLinkRequest(campaign_id="0123456789abcdef", slug="promo", target_url="https://ok.example/x")
    with pytest.raises(InfraError):
        svc.add_link(req)
    assert repo.saved == []


def test_allowed_verdict_creates_the_link() -> None:
    repo = _RecordingRepo()
    svc = CampaignService(repo, _AllowAll())
    req = AddLinkRequest(campaign_id="0123456789abcdef", slug="promo", target_url="https://ok.example/x")
    view = svc.add_link(req)
    assert [link.slug for link in view.links] == ["promo"]
    assert len(repo.saved) == 1
