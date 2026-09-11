from __future__ import annotations

import pytest
import tesser.testing as ts

import reports.application as application
import reports.application.ports as ports
import reports.client as client


@ts.fake
class FakeLinkSource(ports.LinkSource):
    def __init__(
        self, *records: ports.LinkRecord, error: Exception | None = None
    ) -> None:
        self.records = records
        self.error = error
        self.requests: list[ports.ListLinksRequest] = []

    def links(self, list_links_request: ports.ListLinksRequest) -> ports.ListLinksResponse:
        self.requests.append(list_links_request)
        if self.error is not None:
            raise self.error
        return ports.ListLinksResponse(links=self.records)


@ts.fake
class FakeVerdictSource(ports.VerdictSource):
    def __init__(
        self, *records: ports.VerdictRecord, error: Exception | None = None
    ) -> None:
        self.records = records
        self.error = error
        self.requests: list[ports.ListVerdictsRequest] = []

    def verdicts(
        self, list_verdicts_request: ports.ListVerdictsRequest
    ) -> ports.ListVerdictsResponse:
        self.requests.append(list_verdicts_request)
        if self.error is not None:
            raise self.error
        return ports.ListVerdictsResponse(verdicts=self.records)


def test_a_link_is_reported_with_the_verdict_recorded_for_its_target() -> None:
    fake_link_source = FakeLinkSource(
        ports.LinkRecord(slug="spring-sale", target_url="https://a.example/s")
    )
    fake_verdict_source = FakeVerdictSource(
        ports.VerdictRecord(
            target_url="https://a.example/s",
            decision=ports.VerdictDecision.DENIED,
            reason="host blocked",
        )
    )

    links_by_verdict_response = application.ReportsService(fake_link_source, fake_verdict_source).links_by_verdict(
        client.LinksByVerdictRequest()
    )

    assert [(view.slug, view.decision, view.reason) for view in links_by_verdict_response.links] == [
        ("spring-sale", "denied", "host blocked")
    ]


def test_a_link_with_no_recorded_verdict_is_still_reported() -> None:
    fake_link_source = FakeLinkSource(
        ports.LinkRecord(slug="spring-sale", target_url="https://a.example/s")
    )
    fake_verdict_source = FakeVerdictSource()

    links_by_verdict_response = application.ReportsService(fake_link_source, fake_verdict_source).links_by_verdict(
        client.LinksByVerdictRequest()
    )

    assert [view.slug for view in links_by_verdict_response.links] == ["spring-sale"]
    assert links_by_verdict_response.links[0].decision == "allowed"
    assert links_by_verdict_response.links[0].reason == "no verdict recorded"


def test_a_verdict_for_a_target_nobody_links_to_is_left_out() -> None:
    fake_link_source = FakeLinkSource()
    fake_verdict_source = FakeVerdictSource(
        ports.VerdictRecord(
            target_url="https://a.example/orphan",
            decision=ports.VerdictDecision.DENIED,
            reason="host blocked",
        )
    )

    links_by_verdict_response = application.ReportsService(fake_link_source, fake_verdict_source).links_by_verdict(
        client.LinksByVerdictRequest()
    )

    assert links_by_verdict_response.links == ()


def test_the_service_asks_both_sources_once_per_report() -> None:
    fake_link_source = FakeLinkSource()
    fake_verdict_source = FakeVerdictSource()

    application.ReportsService(fake_link_source, fake_verdict_source).links_by_verdict(client.LinksByVerdictRequest())

    assert len(fake_link_source.requests) == 1
    assert len(fake_verdict_source.requests) == 1
    assert isinstance(fake_link_source.requests[0], ports.ListLinksRequest)
    assert isinstance(fake_verdict_source.requests[0], ports.ListVerdictsRequest)


def test_a_denied_link_is_reported_ahead_of_an_allowed_one() -> None:
    fake_link_source = FakeLinkSource(
        ports.LinkRecord(slug="allowed-one", target_url="https://a.example/a"),
        ports.LinkRecord(slug="denied-one", target_url="https://a.example/d"),
    )
    fake_verdict_source = FakeVerdictSource(
        ports.VerdictRecord(
            target_url="https://a.example/d",
            decision=ports.VerdictDecision.DENIED,
            reason="host blocked",
        )
    )

    links_by_verdict_response = application.ReportsService(fake_link_source, fake_verdict_source).links_by_verdict(
        client.LinksByVerdictRequest()
    )

    assert [view.slug for view in links_by_verdict_response.links] == ["denied-one", "allowed-one"]


def test_a_link_source_that_is_down_crosses_as_unavailable_rather_than_halving_the_report() -> None:
    fake_link_source = FakeLinkSource(error=ports.LinkSourceUnavailable("link store unreachable"))
    fake_verdict_source = FakeVerdictSource()

    with pytest.raises(client.Unavailable) as caught:
        application.ReportsService(fake_link_source, fake_verdict_source).links_by_verdict(
            client.LinksByVerdictRequest()
        )

    assert caught.value.message == "the link source is unavailable"
    assert isinstance(caught.value.__cause__, ports.LinkSourceUnavailable)
    assert fake_verdict_source.requests == []


def test_a_verdict_source_that_is_down_crosses_as_unavailable_rather_than_halving_the_report() -> None:
    fake_link_source = FakeLinkSource()
    fake_verdict_source = FakeVerdictSource(
        error=ports.VerdictSourceUnavailable("verdict store unreachable")
    )

    with pytest.raises(client.Unavailable) as caught:
        application.ReportsService(fake_link_source, fake_verdict_source).links_by_verdict(
            client.LinksByVerdictRequest()
        )

    assert caught.value.message == "the verdict source is unavailable"
    assert isinstance(caught.value.__cause__, ports.VerdictSourceUnavailable)


def test_a_link_record_the_domain_would_not_accept_crosses_as_unreadable() -> None:
    fake_link_source = FakeLinkSource(
        ports.LinkRecord(slug="spring-sale", target_url="not-a-url")
    )
    fake_verdict_source = FakeVerdictSource()

    with pytest.raises(client.Unreadable) as caught:
        application.ReportsService(fake_link_source, fake_verdict_source).links_by_verdict(
            client.LinksByVerdictRequest()
        )

    assert caught.value.message.startswith("a record the report cannot read: ")


def test_an_allowed_verdict_member_is_reported_as_an_allowed_link() -> None:
    fake_link_source = FakeLinkSource(
        ports.LinkRecord(slug="spring-sale", target_url="https://a.example/s")
    )
    fake_verdict_source = FakeVerdictSource(
        ports.VerdictRecord(
            target_url="https://a.example/s",
            decision=ports.VerdictDecision.ALLOWED,
            reason="on the allowlist",
        )
    )

    links_by_verdict_response = application.ReportsService(fake_link_source, fake_verdict_source).links_by_verdict(
        client.LinksByVerdictRequest()
    )

    assert [(view.slug, view.decision, view.reason) for view in links_by_verdict_response.links] == [
        ("spring-sale", "allowed", "on the allowlist")
    ]


def test_a_verdict_record_carrying_no_reason_crosses_as_unreadable() -> None:
    fake_link_source = FakeLinkSource()
    fake_verdict_source = FakeVerdictSource(
        ports.VerdictRecord(
            target_url="https://a.example/s",
            decision=ports.VerdictDecision.ALLOWED,
            reason="",
        )
    )

    with pytest.raises(client.Unreadable):
        application.ReportsService(fake_link_source, fake_verdict_source).links_by_verdict(
            client.LinksByVerdictRequest()
        )
