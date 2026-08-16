from __future__ import annotations

import pytest
import tesser.testing as ts

import reports.application.ports.link_source as link_source
import reports.application.ports.verdict_source as verdict_source
import reports.application.service as service
import reports.client.client as client
from tesser.errors import InfraError


@ts.fake
class FakeLinkSource(link_source.LinkSource):
    def __init__(
        self, *records: link_source.LinkRecord, error: Exception | None = None
    ) -> None:
        self.records = records
        self.error = error
        self.requests: list[link_source.ListLinksRequest] = []

    def links(self, request: link_source.ListLinksRequest) -> link_source.ListLinksResponse:
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        return link_source.ListLinksResponse(links=self.records)


@ts.fake
class FakeVerdictSource(verdict_source.VerdictSource):
    def __init__(self, *records: verdict_source.VerdictRecord) -> None:
        self.records = records
        self.requests: list[verdict_source.ListVerdictsRequest] = []

    def verdicts(
        self, request: verdict_source.ListVerdictsRequest
    ) -> verdict_source.ListVerdictsResponse:
        self.requests.append(request)
        return verdict_source.ListVerdictsResponse(verdicts=self.records)


def test_a_link_is_reported_with_the_verdict_recorded_for_its_target() -> None:
    links = FakeLinkSource(
        link_source.LinkRecord(slug="spring-sale", target_url="https://a.example/s")
    )
    verdicts = FakeVerdictSource(
        verdict_source.VerdictRecord(
            target_url="https://a.example/s",
            decision=verdict_source.VerdictDecision.DENIED,
            reason="host blocked",
        )
    )

    resp = service.ReportsService(links, verdicts).links_by_verdict(
        client.LinksByVerdictRequest()
    )

    assert [(view.slug, view.allowed, view.reason) for view in resp.links] == [
        ("spring-sale", False, "host blocked")
    ]


def test_a_link_with_no_recorded_verdict_is_still_reported() -> None:
    links = FakeLinkSource(
        link_source.LinkRecord(slug="spring-sale", target_url="https://a.example/s")
    )
    verdicts = FakeVerdictSource()

    resp = service.ReportsService(links, verdicts).links_by_verdict(
        client.LinksByVerdictRequest()
    )

    assert [view.slug for view in resp.links] == ["spring-sale"]
    assert resp.links[0].allowed is True


def test_a_verdict_for_a_target_nobody_links_to_is_left_out() -> None:
    links = FakeLinkSource()
    verdicts = FakeVerdictSource(
        verdict_source.VerdictRecord(
            target_url="https://a.example/orphan",
            decision=verdict_source.VerdictDecision.DENIED,
            reason="host blocked",
        )
    )

    resp = service.ReportsService(links, verdicts).links_by_verdict(
        client.LinksByVerdictRequest()
    )

    assert resp.links == ()


def test_the_service_asks_both_sources_once_per_report() -> None:
    links = FakeLinkSource()
    verdicts = FakeVerdictSource()

    service.ReportsService(links, verdicts).links_by_verdict(client.LinksByVerdictRequest())

    assert len(links.requests) == 1
    assert len(verdicts.requests) == 1
    assert isinstance(links.requests[0], link_source.ListLinksRequest)
    assert isinstance(verdicts.requests[0], verdict_source.ListVerdictsRequest)


def test_a_denied_link_is_reported_ahead_of_an_allowed_one() -> None:
    links = FakeLinkSource(
        link_source.LinkRecord(slug="allowed-one", target_url="https://a.example/a"),
        link_source.LinkRecord(slug="denied-one", target_url="https://a.example/d"),
    )
    verdicts = FakeVerdictSource(
        verdict_source.VerdictRecord(
            target_url="https://a.example/d",
            decision=verdict_source.VerdictDecision.DENIED,
            reason="host blocked",
        )
    )

    resp = service.ReportsService(links, verdicts).links_by_verdict(
        client.LinksByVerdictRequest()
    )

    assert [view.slug for view in resp.links] == ["denied-one", "allowed-one"]


def test_a_source_that_is_down_fails_the_report_rather_than_halving_it() -> None:
    links = FakeLinkSource(error=InfraError("link store unreachable"))
    verdicts = FakeVerdictSource()

    with pytest.raises(InfraError):
        service.ReportsService(links, verdicts).links_by_verdict(
            client.LinksByVerdictRequest()
        )
