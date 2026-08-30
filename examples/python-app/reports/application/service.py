from __future__ import annotations

import tesser.application as ts

import reports.application.ports.link_source as link_source
import reports.application.ports.verdict_source as verdict_source
import reports.client.client as client
import reports.domain.report as report


class MapToLinkSpec(ts.Mapper, report.LinkSpec):

    def __init__(self, record: link_source.LinkRecord) -> None:
        super().__init__(slug=record.slug, target_url=record.target_url)


class MapToRecordedVerdictSpec(ts.Mapper, report.RecordedVerdictSpec):

    def __init__(self, record: verdict_source.VerdictRecord) -> None:
        super().__init__(
            target_url=record.target_url,
            decision=record.decision.value,
            reason=record.reason,
        )


class MapToLinkVerdictsSpec(ts.Mapper, report.LinkVerdictsSpec):

    def __init__(
        self,
        listed_links: link_source.ListLinksResponse,
        listed_verdicts: verdict_source.ListVerdictsResponse,
    ) -> None:
        super().__init__(
            links=tuple(MapToLinkSpec(record) for record in listed_links.links),
            verdicts=tuple(
                MapToRecordedVerdictSpec(record) for record in listed_verdicts.verdicts
            ),
        )


class MapToLinkVerdictView(ts.Mapper, client.LinkVerdictView):

    def __init__(self, row: report.LinkVerdict) -> None:
        super().__init__(
            slug=str(row.slug),
            target_url=str(row.target_url),
            decision=str(row.decision),
            reason=str(row.reason),
        )


class MapToLinksByVerdictResponse(ts.Mapper, client.LinksByVerdictResponse):

    def __init__(self, joined: report.LinkVerdicts) -> None:
        super().__init__(links=tuple(MapToLinkVerdictView(row) for row in joined.rows))


class ReportsService(ts.ApplicationService):

    def __init__(self, links: link_source.LinkSource, verdicts: verdict_source.VerdictSource) -> None:
        self._links = links
        self._verdicts = verdicts

    def links_by_verdict(self, req: client.LinksByVerdictRequest) -> client.LinksByVerdictResponse:
        listed_links = self._links.links(link_source.ListLinksRequest())
        listed_verdicts = self._verdicts.verdicts(verdict_source.ListVerdictsRequest())
        joined = report.LinkVerdicts(MapToLinkVerdictsSpec(listed_links, listed_verdicts))
        return MapToLinksByVerdictResponse(joined)
