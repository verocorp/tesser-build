from __future__ import annotations

import pytest

from campaign.application.service import CampaignService
from campaign.client import AddLinkRequest, CheckOutcome
from campaign.domain.campaign import Campaign, CampaignSpec
from campaign.domain.money import MoneySpec
from campaign.domain.values import CampaignID, Slug
from errors import DomainError, InfraError, Kind

_CAMPAIGN_ID = "0123456789abcdef"


def _campaign() -> Campaign:
    return Campaign(
        CampaignSpec(id=_CAMPAIGN_ID, budget=MoneySpec(amount="100.00", currency="USD"), links=())
    )


class _RecordingRepo:
    def __init__(self) -> None:
        self._campaign = _campaign()
        self.saved: list[Campaign] = []

    def save(self, c: Campaign) -> None:
        self.saved.append(c)

    def find(self, id: CampaignID) -> Campaign | None:
        return self._campaign if id == self._campaign.id else None

    def find_by_slug(self, slug: Slug) -> Campaign | None:
        return None

    def all(self) -> tuple[Campaign, ...]:
        return (self._campaign,)


class _Blocking:
    def check(self, target_url: str) -> CheckOutcome:
        return CheckOutcome(False, "not on the allow-list")


class _Outage:
    def check(self, target_url: str) -> CheckOutcome:
        raise InfraError("linkpolicy unavailable")


class _AllowAll:
    def check(self, target_url: str) -> CheckOutcome:
        return CheckOutcome(True, "ok")


_REQ = AddLinkRequest(campaign_id=_CAMPAIGN_ID, slug="promo", target_url="https://ok.example/x")


def test_rejection_is_a_conflict_and_creates_nothing() -> None:
    repo = _RecordingRepo()
    svc = CampaignService(repo, _Blocking())
    with pytest.raises(DomainError) as caught:
        svc.add_link(_REQ)
    assert caught.value.kind is Kind.CONFLICT
    assert repo.saved == []


def test_outage_propagates_and_creates_nothing() -> None:
    repo = _RecordingRepo()
    svc = CampaignService(repo, _Outage())
    with pytest.raises(InfraError):
        svc.add_link(_REQ)
    assert repo.saved == []


def test_allowed_verdict_creates_the_link() -> None:
    repo = _RecordingRepo()
    svc = CampaignService(repo, _AllowAll())
    view = svc.add_link(_REQ)
    assert [link.slug for link in view.links] == ["promo"]
    assert len(repo.saved) == 1
