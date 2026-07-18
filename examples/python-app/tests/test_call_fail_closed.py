"""Moment 1 — the synchronous, fail-closed cross-context call. A policy rejection
becomes a domain conflict and creates nothing; a checker outage propagates as an
InfraError and creates nothing. Only an allowed verdict creates the link.
"""

from __future__ import annotations

import pytest

from campaign.application.service import CampaignService
from campaign.client import CheckOutcome, CreateLinkRequest
from campaign.domain.short_link import ShortLink
from campaign.domain.values import Slug
from errors import DomainError, InfraError, Kind


class _RecordingRepo:
    def __init__(self) -> None:
        self.saved: list[ShortLink] = []

    def save(self, link: ShortLink) -> None:
        self.saved.append(link)

    def find(self, slug: Slug) -> ShortLink | None:
        return None

    def all(self) -> tuple[ShortLink, ...]:
        return tuple(self.saved)


class _Blocking:
    def check(self, target_url: str) -> CheckOutcome:
        return CheckOutcome(False, "not on the allow-list")


class _Outage:
    def check(self, target_url: str) -> CheckOutcome:
        raise InfraError("linkpolicy unavailable")


class _AllowAll:
    def check(self, target_url: str) -> CheckOutcome:
        return CheckOutcome(True, "ok")


_REQ = CreateLinkRequest(slug="promo", target_url="https://ok.example/x")


def test_rejection_is_a_conflict_and_creates_nothing() -> None:
    repo = _RecordingRepo()
    svc = CampaignService(repo, _Blocking())
    with pytest.raises(DomainError) as caught:
        svc.create_link(_REQ)
    assert caught.value.kind is Kind.CONFLICT
    assert repo.saved == []


def test_outage_propagates_and_creates_nothing() -> None:
    repo = _RecordingRepo()
    svc = CampaignService(repo, _Outage())
    with pytest.raises(InfraError):
        svc.create_link(_REQ)
    assert repo.saved == []


def test_allowed_verdict_creates_the_link() -> None:
    repo = _RecordingRepo()
    svc = CampaignService(repo, _AllowAll())
    resp = svc.create_link(_REQ)
    assert resp.slug == "promo"
    assert len(repo.saved) == 1
