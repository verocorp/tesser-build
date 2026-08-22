from __future__ import annotations

import tesser.testing as ts

from protocol.http import Endpoint, HttpRequest, HttpResponse
from srv.http.router import Route, match


@ts.fake
class FakeEndpointNamed(Endpoint):
    def __init__(self, name: str) -> None:
        self.name = name
        self.calls = 0

    def __call__(self, request: HttpRequest, /) -> HttpResponse:
        self.calls += 1
        return HttpResponse.json(200, {"endpoint": self.name})


def test_an_exact_path_matches_its_route_and_captures_nothing() -> None:
    endpoint = FakeEndpointNamed("create")
    found = match((Route("POST", "/campaigns", endpoint),), "POST", "/campaigns")
    assert found is not None
    assert found.endpoint is endpoint
    assert found.path_params == {}
    assert found.query_params == {}


def test_a_path_parameter_is_captured_by_name() -> None:
    endpoint = FakeEndpointNamed("get")
    found = match((Route("GET", "/campaigns/{campaign_id}", endpoint),), "GET", "/campaigns/c-1")
    assert found is not None
    assert found.path_params == {"campaign_id": "c-1"}


def test_a_path_parameter_is_percent_decoded() -> None:
    endpoint = FakeEndpointNamed("resolve")
    found = match((Route("GET", "/r/{slug}", endpoint),), "GET", "/r/summer%20sale")
    assert found is not None
    assert found.path_params == {"slug": "summer sale"}


def test_a_method_mismatch_matches_nothing() -> None:
    routes = (Route("POST", "/campaigns", FakeEndpointNamed("create")),)
    assert match(routes, "GET", "/campaigns") is None


def test_an_unknown_path_matches_nothing() -> None:
    routes = (Route("GET", "/campaigns", FakeEndpointNamed("list")),)
    assert match(routes, "GET", "/nope") is None


def test_a_longer_path_matches_nothing() -> None:
    routes = (Route("GET", "/campaigns/{campaign_id}", FakeEndpointNamed("get")),)
    assert match(routes, "GET", "/campaigns/c-1/links") is None


def test_an_empty_parameter_segment_matches_nothing() -> None:
    routes = (Route("GET", "/r/{slug}", FakeEndpointNamed("resolve")),)
    assert match(routes, "GET", "/r//") is None


def test_a_trailing_slash_still_matches() -> None:
    endpoint = FakeEndpointNamed("create")
    found = match((Route("POST", "/campaigns", endpoint),), "POST", "/campaigns/")
    assert found is not None
    assert found.endpoint is endpoint


def test_query_parameters_ride_along_with_the_match() -> None:
    endpoint = FakeEndpointNamed("report")
    routes = (Route("GET", "/reports/links-by-verdict", endpoint),)
    found = match(routes, "GET", "/reports/links-by-verdict?allowed=true&limit=10")
    assert found is not None
    assert found.query_params == {"allowed": "true", "limit": "10"}


def test_a_repeated_query_parameter_takes_its_last_value() -> None:
    endpoint = FakeEndpointNamed("report")
    routes = (Route("GET", "/reports/links-by-verdict", endpoint),)
    found = match(routes, "GET", "/reports/links-by-verdict?allowed=true&allowed=false")
    assert found is not None
    assert found.query_params == {"allowed": "false"}


def test_the_first_declared_route_wins() -> None:
    first = FakeEndpointNamed("first")
    second = FakeEndpointNamed("second")
    routes = (Route("GET", "/r/{slug}", first), Route("GET", "/r/{other}", second))
    found = match(routes, "GET", "/r/summer")
    assert found is not None
    assert found.endpoint is first


def test_the_matched_endpoint_is_the_one_that_answers() -> None:
    endpoint = FakeEndpointNamed("create")
    found = match((Route("POST", "/campaigns", endpoint),), "POST", "/campaigns")
    assert found is not None
    resp = found.endpoint(HttpRequest("POST", "/campaigns", {}, {}, {}, b""))
    assert endpoint.calls == 1
    assert resp.json_body() == {"endpoint": "create"}

