from __future__ import annotations

import tesser.application as ts

import reports.application.ports.link_source as link_source
import reports.application.ports.verdict_source as verdict_source
import reports.client.client as client
import reports.domain.report as report


@ts.do_not_use_function
def domain_links(listed: link_source.ListLinksResponse) -> tuple[report.Link, ...]:
    return tuple(report.Link(slug=f.slug, target_url=f.target_url) for f in listed.links)


@ts.do_not_use_function
def domain_verdicts(listed: verdict_source.ListVerdictsResponse) -> tuple[report.RecordedVerdict, ...]:
    return tuple(
        report.RecordedVerdict(f.target_url, f.decision == verdict_source.VerdictDecision.ALLOWED, f.reason)
        for f in listed.verdicts
    )


@ts.do_not_use_function
def links_by_verdict_response(rows: tuple[report.LinkVerdict, ...]) -> client.LinksByVerdictResponse:
    views = tuple(
        client.LinkVerdictView(str(r.slug), str(r.target_url), str(r.allowed) == "allowed", str(r.reason))
        for r in rows
    )
    return client.LinksByVerdictResponse(links=views)
