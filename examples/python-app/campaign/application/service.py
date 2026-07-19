from __future__ import annotations

from typing import Protocol

from campaign.client import (
    CreateLinkRequest,
    CreateLinkResponse,
    LinkView,
    ResolveRequest,
    ResolveResponse,
    TargetChecker,
)
from campaign.domain.short_link import ShortLink
from campaign.domain.values import Slug, TargetURL
from errors import conflict, not_found


class LinkRepository(Protocol):

    def save(self, link: ShortLink) -> None: ...

    def find(self, slug: Slug) -> ShortLink | None: ...

    def all(self) -> tuple[ShortLink, ...]: ...


class CampaignService:
    def __init__(self, repo: LinkRepository, checker: TargetChecker) -> None:
        self._repo = repo
        self._checker = checker

    def create_link(self, req: CreateLinkRequest) -> CreateLinkResponse:
        slug = Slug(req.slug)
        target = TargetURL(req.target_url)
        outcome = self._checker.check(target.value)
        if not outcome.allowed:
            raise conflict("destination_blocked", f"destination not allowed: {outcome.reason}")
        if self._repo.find(slug) is not None:
            raise conflict("duplicate_slug", f"slug {req.slug!r} already exists")
        self._repo.save(ShortLink(slug, target))
        return CreateLinkResponse(slug=slug.value, target_url=target.value)

    def resolve(self, req: ResolveRequest) -> ResolveResponse:
        link = self._repo.find(Slug(req.slug))
        if link is None or not link.active:
            raise not_found("link_missing", f"no active link for slug {req.slug!r}")
        return ResolveResponse(target_url=link.target.value)

    def list_links(self) -> tuple[LinkView, ...]:
        return tuple(
            LinkView(slug=link.slug.value, target_url=link.target.value, active=link.active)
            for link in self._repo.all()
        )
