"""The campaign application service: convert -> delegate -> persist -> respond.

``create_link`` is Moment 1: it vets the destination through the ``TargetChecker``
port SYNCHRONOUSLY and FAIL-CLOSED. A rejection becomes a domain ``conflict``; an
outage surfaces as an ``InfraError`` from the checker and PROPAGATES untouched —
either way no link is created. This is the opposite of a best-effort telemetry
write, and it is why coupling the two contexts here is correct.

It satisfies ``campaign.Client`` structurally. The repository port is declared
here, beside its only consumer.
"""

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
    """Outbound port owned by the application, satisfied by an adapter in
    ``adapters/gateways``."""

    def save(self, link: ShortLink) -> None: ...

    def find(self, slug: Slug) -> ShortLink | None: ...

    def all(self) -> tuple[ShortLink, ...]: ...


class CampaignService:
    def __init__(self, repo: LinkRepository, checker: TargetChecker) -> None:
        self._repo = repo
        self._checker = checker

    def create_link(self, req: CreateLinkRequest) -> CreateLinkResponse:
        slug = Slug(req.slug)  # validation in the domain
        target = TargetURL(req.target_url)  # validation in the domain
        outcome = self._checker.check(target.value)  # Moment 1: synchronous, fail-closed
        if not outcome.allowed:  # a policy rejection -> refuse to create
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
