from __future__ import annotations

import tesser.application as ts

import reports.application.ports as ports
import reports.client as client
import reports.domain as domain


class MapToLinkSpec(ts.Mapper, domain.LinkSpec):

    def __init__(self, link_record: ports.LinkRecord) -> None:
        super().__init__(slug=link_record.slug, target_url=link_record.target_url)


class MapToRecordedVerdictSpec(ts.Mapper, domain.RecordedVerdictSpec):

    def __init__(self, verdict_record: ports.VerdictRecord) -> None:
        super().__init__(
            target_url=verdict_record.target_url,
            decision=verdict_record.decision.value,
            reason=verdict_record.reason,
        )


class MapToLinkVerdictsSpec(ts.Mapper, domain.LinkVerdictsSpec):

    def __init__(
        self,
        list_links_response: ports.ListLinksResponse,
        list_verdicts_response: ports.ListVerdictsResponse,
    ) -> None:
        super().__init__(
            links=tuple(MapToLinkSpec(record) for record in list_links_response.links),
            verdicts=tuple(
                MapToRecordedVerdictSpec(record) for record in list_verdicts_response.verdicts
            ),
        )


class MapToLinkVerdictView(ts.Mapper, client.LinkVerdictView):

    def __init__(self, link_verdict: domain.LinkVerdict) -> None:
        super().__init__(
            slug=str(link_verdict.slug),
            target_url=str(link_verdict.target_url),
            decision=str(link_verdict.decision),
            reason=str(link_verdict.reason),
        )


class MapToLinksByVerdictResponse(ts.Mapper, client.LinksByVerdictResponse):

    def __init__(self, link_verdicts: domain.LinkVerdicts) -> None:
        super().__init__(links=tuple(MapToLinkVerdictView(row) for row in link_verdicts.rows))


class ReportsService(ts.ApplicationService):

    def __init__(self, link_source: ports.LinkSource, verdict_source: ports.VerdictSource) -> None:
        self._link_source = link_source
        self._verdict_source = verdict_source

    def links_by_verdict(
        self, links_by_verdict_request: client.LinksByVerdictRequest
    ) -> client.LinksByVerdictResponse:
        list_links_response = self._link_source.links(ports.ListLinksRequest())
        list_verdicts_response = self._verdict_source.verdicts(ports.ListVerdictsRequest())
        link_verdicts = domain.LinkVerdicts(
            MapToLinkVerdictsSpec(list_links_response, list_verdicts_response)
        )
        return MapToLinksByVerdictResponse(link_verdicts)
