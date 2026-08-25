from __future__ import annotations

import tesser.application as ts

import reports.application.ports.link_source as link_source
import reports.application.ports.verdict_source as verdict_source
import reports.client.client as client
import reports.domain.report as report


class ReportsService(ts.ApplicationService):

    def __init__(self, links: link_source.LinkSource, verdicts: verdict_source.VerdictSource) -> None:
        self._links = links
        self._verdicts = verdicts

    def links_by_verdict(self, req: client.LinksByVerdictRequest) -> client.LinksByVerdictResponse:
        listed_links = self._links.links(link_source.ListLinksRequest())
        links = tuple(
            report.Link(report.LinkSpec(slug=f.slug, target_url=f.target_url))
            for f in listed_links.links
        )
        listed_verdicts = self._verdicts.verdicts(verdict_source.ListVerdictsRequest())
        verdicts = tuple(
            report.RecordedVerdict(
                report.RecordedVerdictSpec(
                    f.target_url, f.decision == verdict_source.VerdictDecision.ALLOWED, f.reason
                )
            )
            for f in listed_verdicts.verdicts
        )
        by_url = {str(v.target_url): v for v in verdicts}
        joined: list[report.LinkVerdict] = []
        for link in links:
            link_slug = str(link.slug)
            link_target = str(link.target_url)
            link_allowed = (
                str(by_url[link_target].allowed) == "allowed" if link_target in by_url else True
            )
            link_reason = (
                str(by_url[link_target].reason)
                if link_target in by_url
                else "no verdict recorded"
            )
            joined.append(
                report.LinkVerdict(
                    report.LinkVerdictSpec(
                        slug=link_slug,
                        target_url=link_target,
                        allowed=link_allowed,
                        reason=link_reason,
                    )
                )
            )
        joined.sort(key=lambda r: (str(r.allowed) == "allowed", str(r.slug)))
        rows = tuple(joined)
        views: list[client.LinkVerdictView] = []
        for row in rows:
            slug = str(row.slug)
            target_url = str(row.target_url)
            decision = str(row.allowed)
            reason = str(row.reason)
            view = client.LinkVerdictView(slug, target_url, decision == "allowed", reason)
            views.append(view)
        listed = tuple(views)
        return client.LinksByVerdictResponse(links=listed)
