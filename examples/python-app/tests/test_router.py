from __future__ import annotations

import protocol.http as http
import tests.support as support


def test_a_literal_route_matches_exactly() -> None:
    found = http.Router(support.ROUTES).match("GET", "/reports/links-by-verdict")
    assert found is not None
    assert found.endpoint is support.route_other
    assert found.path_params == {}


def test_a_pattern_route_extracts_its_parameter() -> None:
    found = http.Router(support.ROUTES).match("GET", "/campaigns/abc123")
    assert found is not None
    assert found.path_params == {"campaign_id": "abc123"}


def test_the_method_is_part_of_the_match() -> None:
    assert http.Router(support.ROUTES).match("GET", "/campaigns") is None
    assert http.Router(support.ROUTES).match("POST", "/campaigns") is not None


def test_an_unknown_path_does_not_match() -> None:
    assert http.Router(support.ROUTES).match("GET", "/nope") is None
    assert http.Router(support.ROUTES).match("GET", "/campaigns/abc/extra") is None


def test_a_query_string_is_parsed_and_never_part_of_the_path_match() -> None:
    found = http.Router(support.ROUTES).match("GET", "/campaigns/abc123?verbose=1&page=2")
    assert found is not None
    assert found.path_params == {"campaign_id": "abc123"}
    assert found.query_params == {"verbose": "1", "page": "2"}


def test_a_percent_encoded_parameter_is_decoded() -> None:
    found = http.Router(support.ROUTES).match("GET", "/r/summer%20sale")
    assert found is not None
    assert found.path_params == {"slug": "summer sale"}

