from __future__ import annotations

import pytest
import tesser.testing as ts

import reports.adapters.handlers as handlers
import reports.client as client
import protocol as protocol
import tesser.errors as errors


@ts.fake
class FakeReportsClient(client.ReportsClient):
    def __init__(
        self, *views: client.LinkVerdictView, error: Exception | None = None
    ) -> None:
        self.views = views
        self.error = error
        self.requests: list[client.LinksByVerdictRequest] = []

    def links_by_verdict(
        self, links_by_verdict_request: client.LinksByVerdictRequest
    ) -> client.LinksByVerdictResponse:
        self.requests.append(links_by_verdict_request)
        if self.error is not None:
            raise self.error
        return client.LinksByVerdictResponse(links=self.views)


def test_a_report_comes_back_as_a_json_object_of_link_rows() -> None:
    fake_reports_client = FakeReportsClient(
        client.LinkVerdictView("spring-sale", "https://a.example/s", "denied", "host blocked")
    )

    http_response = handlers.HttpHandler(fake_reports_client).links_by_verdict(
        protocol.HttpRequest("GET", "/reports/links", {}, {}, {}, b"")
    )

    assert http_response.status_code == 200
    assert http_response.json_body() == {
        "links": [
            {
                "slug": "spring-sale",
                "target_url": "https://a.example/s",
                "decision": "denied",
                "reason": "host blocked",
            }
        ]
    }


def test_every_row_the_client_serves_reaches_the_body_in_order() -> None:
    fake_reports_client = FakeReportsClient(
        client.LinkVerdictView("denied-one", "https://a.example/d", "denied", "host blocked"),
        client.LinkVerdictView("allowed-one", "https://a.example/a", "allowed", "on the allowlist"),
    )

    http_response = handlers.HttpHandler(fake_reports_client).links_by_verdict(
        protocol.HttpRequest("GET", "/reports/links", {}, {}, {}, b"")
    )

    rows = http_response.json_body()["links"]
    assert isinstance(rows, list)
    assert [row["slug"] for row in rows] == ["denied-one", "allowed-one"]


def test_an_empty_report_is_an_empty_list_and_not_an_error() -> None:
    fake_reports_client = FakeReportsClient()

    http_response = handlers.HttpHandler(fake_reports_client).links_by_verdict(
        protocol.HttpRequest("GET", "/reports/links", {}, {}, {}, b"")
    )

    assert http_response.status_code == 200
    assert http_response.json_body() == {"links": []}


def test_the_handler_declares_json_on_the_way_out() -> None:
    fake_reports_client = FakeReportsClient()

    http_response = handlers.HttpHandler(fake_reports_client).links_by_verdict(
        protocol.HttpRequest("GET", "/reports/links", {}, {}, {}, b"")
    )

    assert http_response.headers["Content-Type"] == "application/json"


def test_the_handler_asks_its_own_client_once() -> None:
    fake_reports_client = FakeReportsClient()

    handlers.HttpHandler(fake_reports_client).links_by_verdict(
        protocol.HttpRequest("GET", "/reports/links", {}, {}, {}, b"")
    )

    assert len(fake_reports_client.requests) == 1
    assert isinstance(fake_reports_client.requests[0], client.LinksByVerdictRequest)


def test_a_client_failure_leaves_the_handler_rather_than_becoming_a_body() -> None:
    fake_reports_client = FakeReportsClient(error=errors.InfraError("reports unavailable"))

    with pytest.raises(errors.InfraError):
        handlers.HttpHandler(fake_reports_client).links_by_verdict(
            protocol.HttpRequest("GET", "/reports/links", {}, {}, {}, b"")
        )
