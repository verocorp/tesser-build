from __future__ import annotations

import protocol as protocol
import tesser.testing as ts


@ts.fake
class FakePathEndpoint(protocol.Endpoint):

    def __call__(self, http_request: protocol.HttpRequest) -> protocol.HttpResponse:
        return protocol.HttpResponse.json(200, {"seen": dict(http_request.path_params)})


@ts.fake
class FakeEmptyEndpoint(protocol.Endpoint):

    def __call__(self, http_request: protocol.HttpRequest) -> protocol.HttpResponse:
        return protocol.HttpResponse.json(200, {})


def test_a_literal_route_matches_exactly() -> None:
    fake_path_endpoint = FakePathEndpoint()
    fake_empty_endpoint = FakeEmptyEndpoint()
    routes = (
        protocol.Route("POST", "/campaigns", fake_empty_endpoint),
        protocol.Route("GET", "/campaigns/{campaign_id}", fake_path_endpoint),
        protocol.Route("GET", "/r/{slug}", fake_path_endpoint),
        protocol.Route("GET", "/reports/links-by-verdict", fake_empty_endpoint),
    )
    found = protocol.Router(routes).match("GET", "/reports/links-by-verdict")
    assert found is not None
    assert found.endpoint is fake_empty_endpoint
    assert found.path_params == {}


def test_a_pattern_route_extracts_its_parameter() -> None:
    fake_path_endpoint = FakePathEndpoint()
    fake_empty_endpoint = FakeEmptyEndpoint()
    routes = (
        protocol.Route("POST", "/campaigns", fake_empty_endpoint),
        protocol.Route("GET", "/campaigns/{campaign_id}", fake_path_endpoint),
        protocol.Route("GET", "/r/{slug}", fake_path_endpoint),
        protocol.Route("GET", "/reports/links-by-verdict", fake_empty_endpoint),
    )
    found = protocol.Router(routes).match("GET", "/campaigns/abc123")
    assert found is not None
    assert found.path_params == {"campaign_id": "abc123"}


def test_the_method_is_part_of_the_match() -> None:
    fake_path_endpoint = FakePathEndpoint()
    fake_empty_endpoint = FakeEmptyEndpoint()
    routes = (
        protocol.Route("POST", "/campaigns", fake_empty_endpoint),
        protocol.Route("GET", "/campaigns/{campaign_id}", fake_path_endpoint),
        protocol.Route("GET", "/r/{slug}", fake_path_endpoint),
        protocol.Route("GET", "/reports/links-by-verdict", fake_empty_endpoint),
    )
    assert protocol.Router(routes).match("GET", "/campaigns") is None
    assert protocol.Router(routes).match("POST", "/campaigns") is not None


def test_an_unknown_path_does_not_match() -> None:
    fake_path_endpoint = FakePathEndpoint()
    fake_empty_endpoint = FakeEmptyEndpoint()
    routes = (
        protocol.Route("POST", "/campaigns", fake_empty_endpoint),
        protocol.Route("GET", "/campaigns/{campaign_id}", fake_path_endpoint),
        protocol.Route("GET", "/r/{slug}", fake_path_endpoint),
        protocol.Route("GET", "/reports/links-by-verdict", fake_empty_endpoint),
    )
    assert protocol.Router(routes).match("GET", "/nope") is None
    assert protocol.Router(routes).match("GET", "/campaigns/abc/extra") is None


def test_a_query_string_is_parsed_and_never_part_of_the_path_match() -> None:
    fake_path_endpoint = FakePathEndpoint()
    fake_empty_endpoint = FakeEmptyEndpoint()
    routes = (
        protocol.Route("POST", "/campaigns", fake_empty_endpoint),
        protocol.Route("GET", "/campaigns/{campaign_id}", fake_path_endpoint),
        protocol.Route("GET", "/r/{slug}", fake_path_endpoint),
        protocol.Route("GET", "/reports/links-by-verdict", fake_empty_endpoint),
    )
    found = protocol.Router(routes).match("GET", "/campaigns/abc123?verbose=1&page=2")
    assert found is not None
    assert found.path_params == {"campaign_id": "abc123"}
    assert found.query_params == {"verbose": "1", "page": "2"}


def test_a_percent_encoded_parameter_is_decoded() -> None:
    fake_path_endpoint = FakePathEndpoint()
    fake_empty_endpoint = FakeEmptyEndpoint()
    routes = (
        protocol.Route("POST", "/campaigns", fake_empty_endpoint),
        protocol.Route("GET", "/campaigns/{campaign_id}", fake_path_endpoint),
        protocol.Route("GET", "/r/{slug}", fake_path_endpoint),
        protocol.Route("GET", "/reports/links-by-verdict", fake_empty_endpoint),
    )
    found = protocol.Router(routes).match("GET", "/r/summer%20sale")
    assert found is not None
    assert found.path_params == {"slug": "summer sale"}
