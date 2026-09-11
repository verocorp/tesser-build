from __future__ import annotations

import pytest

import tesser.testing as ts

import protocol as protocol


def test_an_empty_body_reads_as_an_empty_object() -> None:
    http_request = protocol.HttpRequest("POST", "/jtbd/j-root/stories", {}, {}, {}, b"")
    assert http_request.json_body() == {}


def test_a_json_object_body_reads_back() -> None:
    http_request = protocol.HttpRequest("POST", "/jtbd/j-root/stories", {}, {}, {}, b'{"given": "a jtbd exists"}')
    assert http_request.json_body() == {"given": "a jtbd exists"}


def test_a_malformed_body_is_a_bad_request() -> None:
    http_request = protocol.HttpRequest("POST", "/jtbd/j-root/stories", {}, {}, {}, b"{not json")
    with pytest.raises(protocol.BadRequest) as caught:
        http_request.json_body()
    assert "malformed JSON" in str(caught.value)


def test_an_undecodable_body_is_a_bad_request() -> None:
    http_request = protocol.HttpRequest("POST", "/jtbd/j-root/stories", {}, {}, {}, b"\xff\xfe")
    with pytest.raises(protocol.BadRequest) as caught:
        http_request.json_body()
    assert "malformed JSON" in str(caught.value)


def test_a_json_array_body_is_a_bad_request() -> None:
    http_request = protocol.HttpRequest("POST", "/jtbd/j-root/stories", {}, {}, {}, b"[1, 2]")
    with pytest.raises(protocol.BadRequest) as caught:
        http_request.json_body()
    assert str(caught.value) == "expected a JSON object"


def test_a_declared_path_parameter_reads_back() -> None:
    http_request = protocol.HttpRequest("POST", "/jtbd/j-root/stories", {"jtbd_id": "j-root"}, {}, {}, b"")
    assert http_request.path_param("jtbd_id") == "j-root"


def test_a_missing_path_parameter_is_a_bad_request() -> None:
    http_request = protocol.HttpRequest("POST", "/jtbd/j-root/stories", {}, {}, {}, b"")
    with pytest.raises(protocol.BadRequest) as caught:
        http_request.path_param("jtbd_id")
    assert str(caught.value) == "missing path parameter: jtbd_id"


def test_an_empty_path_parameter_is_a_bad_request() -> None:
    http_request = protocol.HttpRequest("POST", "/jtbd//stories", {"jtbd_id": ""}, {}, {}, b"")
    with pytest.raises(protocol.BadRequest):
        http_request.path_param("jtbd_id")


def test_a_json_response_declares_its_content_type() -> None:
    resp = protocol.HttpResponse.json(201, {"story_id": "j-root-s0"})
    assert resp.status_code == 201
    assert resp.headers["Content-Type"] == "application/json"
    assert resp.json_body() == {"story_id": "j-root-s0"}


def test_a_declared_content_type_is_left_alone() -> None:
    resp = protocol.HttpResponse.json(200, {}, {"content-type": "application/problem+json"})
    assert resp.headers == {"content-type": "application/problem+json"}


def test_an_html_response_carries_the_page_as_is() -> None:
    resp = protocol.HttpResponse.html(b"<title>Product Specification</title>")
    assert resp.status_code == 200
    assert resp.headers == {"Content-Type": "text/html; charset=utf-8"}
    assert resp.body == b"<title>Product Specification</title>"


def test_a_problem_document_carries_its_type_and_detail() -> None:
    resp = protocol.HttpResponse.problem(404, "not_found", "unknown route")
    assert resp.status_code == 404
    assert resp.json_body() == {"type": "/problems/not_found", "detail": "unknown route"}


@ts.fake
class FakeEndpointNamed(protocol.Endpoint):
    def __init__(self, name: str) -> None:
        self.name = name
        self.calls = 0

    def __call__(self, http_request: protocol.HttpRequest, /) -> protocol.HttpResponse:
        self.calls += 1
        return protocol.HttpResponse.json(200, {"endpoint": self.name})


def test_an_exact_path_matches_its_route_and_captures_nothing() -> None:
    fake_endpoint_named = FakeEndpointNamed("page")
    found = protocol.Router((protocol.Route("GET", "/", fake_endpoint_named),)).match("GET", "/")
    assert found is not None
    assert found.endpoint is fake_endpoint_named
    assert found.path_params == {}
    assert found.query_params == {}


def test_a_path_parameter_is_captured_by_name() -> None:
    fake_endpoint_named = FakeEndpointNamed("add_story")
    routes = (protocol.Route("POST", "/jtbd/{jtbd_id}/stories", fake_endpoint_named),)
    found = protocol.Router(routes).match("POST", "/jtbd/j-root/stories")
    assert found is not None
    assert found.path_params == {"jtbd_id": "j-root"}


def test_a_path_parameter_is_percent_decoded() -> None:
    fake_endpoint_named = FakeEndpointNamed("add_story")
    routes = (protocol.Route("POST", "/jtbd/{jtbd_id}/stories", fake_endpoint_named),)
    found = protocol.Router(routes).match("POST", "/jtbd/j%20root/stories")
    assert found is not None
    assert found.path_params == {"jtbd_id": "j root"}


def test_a_method_mismatch_matches_nothing() -> None:
    routes = (protocol.Route("POST", "/jtbd/{jtbd_id}/stories", FakeEndpointNamed("add_story")),)
    assert protocol.Router(routes).match("GET", "/jtbd/j-root/stories") is None


def test_an_unknown_path_matches_nothing() -> None:
    routes = (protocol.Route("GET", "/", FakeEndpointNamed("page")),)
    assert protocol.Router(routes).match("GET", "/nope") is None


def test_a_longer_path_matches_nothing() -> None:
    routes = (protocol.Route("POST", "/jtbd/{jtbd_id}/stories", FakeEndpointNamed("add_story")),)
    assert protocol.Router(routes).match("POST", "/jtbd/j-root/stories/extra") is None


def test_an_empty_parameter_segment_matches_nothing() -> None:
    routes = (protocol.Route("POST", "/jtbd/{jtbd_id}/stories", FakeEndpointNamed("add_story")),)
    assert protocol.Router(routes).match("POST", "/jtbd//stories") is None


def test_a_trailing_slash_still_matches() -> None:
    fake_endpoint_named = FakeEndpointNamed("add_story")
    routes = (protocol.Route("POST", "/jtbd/{jtbd_id}/stories", fake_endpoint_named),)
    found = protocol.Router(routes).match("POST", "/jtbd/j-root/stories/")
    assert found is not None
    assert found.endpoint is fake_endpoint_named


def test_query_parameters_ride_along_with_the_match() -> None:
    fake_endpoint_named = FakeEndpointNamed("page")
    found = protocol.Router((protocol.Route("GET", "/", fake_endpoint_named),)).match("GET", "/?focus=J1")
    assert found is not None
    assert found.query_params == {"focus": "J1"}


def test_the_matched_endpoint_is_the_one_that_answers() -> None:
    fake_endpoint_named = FakeEndpointNamed("page")
    found = protocol.Router((protocol.Route("GET", "/", fake_endpoint_named),)).match("GET", "/")
    assert found is not None
    resp = found.endpoint(protocol.HttpRequest("GET", "/", {}, {}, {}, b""))
    assert fake_endpoint_named.calls == 1
    assert resp.json_body() == {"endpoint": "page"}
