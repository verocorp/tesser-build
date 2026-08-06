from __future__ import annotations

from typing import Protocol

import tesser.application as ts

from reports.client import LinksByVerdictRequest, LinksByVerdictResponse, LinkVerdictView
from reports.domain.report import Link, RecordedVerdict, join_links_with_verdicts


class LinkFact(ts.Parts):

    def __init__(self, slug: str, target_url: str) -> None:
        self.slug = slug
        self.target_url = target_url


class VerdictFact(ts.Parts):

    def __init__(self, target_url: str, allowed: bool, reason: str) -> None:
        self.target_url = target_url
        self.allowed = allowed
        self.reason = reason


class LinkSource(ts.Port, Protocol):

    def links(self) -> tuple[LinkFact, ...]: ...


class VerdictSource(ts.Port, Protocol):

    def verdicts(self) -> tuple[VerdictFact, ...]: ...


class ReportsService(ts.ApplicationService):

    def __init__(self, links: LinkSource, verdicts: VerdictSource) -> None:
        self._links = links
        self._verdicts = verdicts

    def links_by_verdict(self, req: LinksByVerdictRequest) -> LinksByVerdictResponse:
        links = tuple(Link(slug=f.slug, target_url=f.target_url) for f in self._links.links())
        verdicts = tuple(
            RecordedVerdict(f.target_url, f.allowed, f.reason) for f in self._verdicts.verdicts()
        )
        rows = join_links_with_verdicts(links, verdicts)
        views = tuple(LinkVerdictView(r.slug, r.target_url, r.allowed, r.reason) for r in rows)
        return LinksByVerdictResponse(links=views)
