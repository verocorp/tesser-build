from __future__ import annotations

import pytest
import tesser.testing as ts

import reports.adapters.handlers.http as http
import reports.client.client as client
import protocol.http as protocol_http
import tesser.errors as errors


@ts.fake
class FakeReportsClient(client.Client):
    def __init__(
        self, *views: client.LinkVerdictView, error: Exception | None = None
    ) -> None:
        self.views = views
        self.error = error
        self.requests: list[client.LinksByVerdictRequest] = []

    def links_by_verdict(
        self, req: client.LinksByVerdictRequest
    ) -> client.LinksByVerdictResponse:
        self.requests.append(req)
        if self.error is not None:
            raise self.error
        return client.LinksByVerdictResponse(links=self.views)


def test_a_report_comes_back_as_a_json_object_of_link_rows() -> None:
    reports = FakeReportsClient(
        client.LinkVerdictView("spring-sale", "https://a.example/s", "denied", "host blocked")
    )

    resp = http.Handler(reports).links_by_verdict(
        protocol_http.HttpRequest("GET", "/reports/links", {}, {}, {}, b"")
    )

    assert resp.status_code == 200
    assert resp.json_body() == {
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
    reports = FakeReportsClient(
        client.LinkVerdictView("denied-one", "https://a.example/d", "denied", "host blocked"),
        client.LinkVerdictView("allowed-one", "https://a.example/a", "allowed", "on the allowlist"),
    )

    resp = http.Handler(reports).links_by_verdict(
        protocol_http.HttpRequest("GET", "/reports/links", {}, {}, {}, b"")
    )

    rows = resp.json_body()["links"]
    assert isinstance(rows, list)
    assert [row["slug"] for row in rows] == ["denied-one", "allowed-one"]


def test_an_empty_report_is_an_empty_list_and_not_an_error() -> None:
    reports = FakeReportsClient()

    resp = http.Handler(reports).links_by_verdict(
        protocol_http.HttpRequest("GET", "/reports/links", {}, {}, {}, b"")
    )

    assert resp.status_code == 200
    assert resp.json_body() == {"links": []}


def test_the_handler_declares_json_on_the_way_out() -> None:
    reports = FakeReportsClient()

    resp = http.Handler(reports).links_by_verdict(
        protocol_http.HttpRequest("GET", "/reports/links", {}, {}, {}, b"")
    )

    assert resp.headers["Content-Type"] == "application/json"


def test_the_handler_asks_its_own_client_once() -> None:
    reports = FakeReportsClient()

    http.Handler(reports).links_by_verdict(
        protocol_http.HttpRequest("GET", "/reports/links", {}, {}, {}, b"")
    )

    assert len(reports.requests) == 1
    assert isinstance(reports.requests[0], client.LinksByVerdictRequest)


def test_a_client_failure_leaves_the_handler_rather_than_becoming_a_body() -> None:
    reports = FakeReportsClient(error=errors.InfraError("reports unavailable"))

    with pytest.raises(errors.InfraError):
        http.Handler(reports).links_by_verdict(
            protocol_http.HttpRequest("GET", "/reports/links", {}, {}, {}, b"")
        )
