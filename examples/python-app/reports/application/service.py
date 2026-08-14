from __future__ import annotations

import tesser.application as ts

import reports.application.ports.link_source as link_source
import reports.application.ports.verdict_source as verdict_source
import reports.application.views as reports_views
import reports.client.client as client
import reports.domain.report as report


class ReportsService(ts.ApplicationService):

    def __init__(self, links: link_source.LinkSource, verdicts: verdict_source.VerdictSource) -> None:
        self._links = links
        self._verdicts = verdicts

    def links_by_verdict(self, req: client.LinksByVerdictRequest) -> client.LinksByVerdictResponse:
        links = reports_views.domain_links(self._links.links(link_source.ListLinksRequest()))
        verdicts = reports_views.domain_verdicts(self._verdicts.verdicts(verdict_source.ListVerdictsRequest()))
        rows = report.join_links_with_verdicts(links, verdicts)
        return reports_views.links_by_verdict_response(rows)
