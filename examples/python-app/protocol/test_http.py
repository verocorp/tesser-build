from __future__ import annotations

import pytest

import tesser.testing as ts

import protocol.http as http


def test_an_empty_body_reads_as_an_empty_object() -> None:
    req = http.HttpRequest("POST", "/campaigns", {}, {}, {}, b"")
    assert req.json_body() == {}


def test_a_json_object_body_reads_back() -> None:
    req = http.HttpRequest("POST", "/campaigns", {}, {}, {}, b'{"budget_amount": "100.00"}')
    assert req.json_body() == {"budget_amount": "100.00"}


def test_a_malformed_body_is_a_bad_request() -> None:
    req = http.HttpRequest("POST", "/campaigns", {}, {}, {}, b"{not json")
    with pytest.raises(http.BadRequest) as caught:
        req.json_body()
    assert "malformed JSON" in str(caught.value)


def test_an_undecodable_body_is_a_bad_request() -> None:
    req = http.HttpRequest("POST", "/campaigns", {}, {}, {}, b"\xff\xfe")
    with pytest.raises(http.BadRequest) as caught:
        req.json_body()
    assert "malformed JSON" in str(caught.value)


def test_a_json_array_body_is_a_bad_request() -> None:
    req = http.HttpRequest("POST", "/campaigns", {}, {}, {}, b"[1, 2]")
    with pytest.raises(http.BadRequest) as caught:
        req.json_body()
    assert str(caught.value) == "expected a JSON object"


def test_a_json_scalar_body_is_a_bad_request() -> None:
    req = http.HttpRequest("POST", "/campaigns", {}, {}, {}, b'"a string"')
    with pytest.raises(http.BadRequest):
        req.json_body()


def test_a_declared_path_parameter_reads_back() -> None:
    req = http.HttpRequest("GET", "/r/summer", {"slug": "summer"}, {}, {}, b"")
    assert req.path_param("slug") == "summer"


def test_a_missing_path_parameter_is_a_bad_request() -> None:
    req = http.HttpRequest("GET", "/r/summer", {"slug": "summer"}, {}, {}, b"")
    with pytest.raises(http.BadRequest) as caught:
        req.path_param("campaign_id")
    assert str(caught.value) == "missing path parameter: campaign_id"


def test_an_empty_path_parameter_is_a_bad_request() -> None:
    req = http.HttpRequest("GET", "/r/", {"slug": ""}, {}, {}, b"")
    with pytest.raises(http.BadRequest):
        req.path_param("slug")


def test_a_json_response_declares_its_content_type() -> None:
    resp = http.HttpResponse.json(201, {"campaign_id": "c-1"})
    assert resp.status_code == 201
    assert resp.headers["Content-Type"] == "application/json"
    assert resp.json_body() == {"campaign_id": "c-1"}


def test_a_declared_content_type_is_left_alone() -> None:
    resp = http.HttpResponse.json(200, {}, {"content-type": "application/problem+json"})
    assert resp.headers == {"content-type": "application/problem+json"}


def test_a_problem_document_carries_its_type_and_detail() -> None:
    resp = http.HttpResponse.problem(422, "bad_amount", "budget must be positive")
    assert resp.status_code == 422
    assert resp.json_body() == {
        "type": "/problems/bad_amount",
        "detail": "budget must be positive",
    }


def test_a_redirect_carries_a_location_and_an_empty_body() -> None:
    resp = http.HttpResponse.redirect("https://ok.example/a")
    assert resp.status_code == 302
    assert resp.headers == {"Location": "https://ok.example/a"}
    assert resp.body == b""


def test_a_redirect_takes_a_declared_status() -> None:
    assert http.HttpResponse.redirect("https://ok.example/a", 301).status_code == 301


def test_a_redirect_target_carrying_a_control_character_is_rejected() -> None:
    for target in ("https://ok.example/a\r\nSet-Cookie: x=1", "https://ok.example/a\n", "https://ok.example/\x00"):
        with pytest.raises(http.BadRequest) as caught:
            http.HttpResponse.redirect(target)
        assert "control character" in str(caught.value)


@ts.fake
class FakeEndpointNamed(http.Endpoint):
    def __init__(self, name: str) -> None:
        self.name = name
        self.calls = 0

    def __call__(self, request: http.HttpRequest, /) -> http.HttpResponse:
        self.calls += 1
        return http.HttpResponse.json(200, {"endpoint": self.name})


def test_an_exact_path_matches_its_route_and_captures_nothing() -> None:
    endpoint = FakeEndpointNamed("create")
    found = http.Router((http.Route("POST", "/campaigns", endpoint),)).match("POST", "/campaigns")
    assert found is not None
    assert found.endpoint is endpoint
    assert found.path_params == {}
    assert found.query_params == {}


def test_a_path_parameter_is_captured_by_name() -> None:
    endpoint = FakeEndpointNamed("get")
    found = http.Router((http.Route("GET", "/campaigns/{campaign_id}", endpoint),)).match("GET", "/campaigns/c-1")
    assert found is not None
    assert found.path_params == {"campaign_id": "c-1"}


def test_a_path_parameter_is_percent_decoded() -> None:
    endpoint = FakeEndpointNamed("resolve")
    found = http.Router((http.Route("GET", "/r/{slug}", endpoint),)).match("GET", "/r/summer%20sale")
    assert found is not None
    assert found.path_params == {"slug": "summer sale"}


def test_a_method_mismatch_matches_nothing() -> None:
    routes = (http.Route("POST", "/campaigns", FakeEndpointNamed("create")),)
    assert http.Router(routes).match("GET", "/campaigns") is None


def test_an_unknown_path_matches_nothing() -> None:
    routes = (http.Route("GET", "/campaigns", FakeEndpointNamed("list")),)
    assert http.Router(routes).match("GET", "/nope") is None


def test_a_longer_path_matches_nothing() -> None:
    routes = (http.Route("GET", "/campaigns/{campaign_id}", FakeEndpointNamed("get")),)
    assert http.Router(routes).match("GET", "/campaigns/c-1/links") is None


def test_an_empty_parameter_segment_matches_nothing() -> None:
    routes = (http.Route("GET", "/r/{slug}", FakeEndpointNamed("resolve")),)
    assert http.Router(routes).match("GET", "/r//") is None


def test_a_trailing_slash_still_matches() -> None:
    endpoint = FakeEndpointNamed("create")
    found = http.Router((http.Route("POST", "/campaigns", endpoint),)).match("POST", "/campaigns/")
    assert found is not None
    assert found.endpoint is endpoint


def test_query_parameters_ride_along_with_the_match() -> None:
    endpoint = FakeEndpointNamed("report")
    routes = (http.Route("GET", "/reports/links-by-verdict", endpoint),)
    found = http.Router(routes).match("GET", "/reports/links-by-verdict?allowed=true&limit=10")
    assert found is not None
    assert found.query_params == {"allowed": "true", "limit": "10"}


def test_a_repeated_query_parameter_takes_its_last_value() -> None:
    endpoint = FakeEndpointNamed("report")
    routes = (http.Route("GET", "/reports/links-by-verdict", endpoint),)
    found = http.Router(routes).match("GET", "/reports/links-by-verdict?allowed=true&allowed=false")
    assert found is not None
    assert found.query_params == {"allowed": "false"}


def test_the_first_declared_route_wins() -> None:
    first = FakeEndpointNamed("first")
    second = FakeEndpointNamed("second")
    routes = (http.Route("GET", "/r/{slug}", first), http.Route("GET", "/r/{other}", second))
    found = http.Router(routes).match("GET", "/r/summer")
    assert found is not None
    assert found.endpoint is first


def test_the_matched_endpoint_is_the_one_that_answers() -> None:
    endpoint = FakeEndpointNamed("create")
    found = http.Router((http.Route("POST", "/campaigns", endpoint),)).match("POST", "/campaigns")
    assert found is not None
    resp = found.endpoint(http.HttpRequest("POST", "/campaigns", {}, {}, {}, b""))
    assert endpoint.calls == 1
    assert resp.json_body() == {"endpoint": "create"}
