from __future__ import annotations

from srv.http.router import match, split
from tests.support import ROUTES, route_other


def test_a_literal_route_matches_exactly() -> None:
    found = match(ROUTES, "GET", "/reports/links-by-verdict")
    assert found is not None
    assert found.endpoint is route_other
    assert found.path_params == {}


def test_a_pattern_route_extracts_its_parameter() -> None:
    found = match(ROUTES, "GET", "/campaigns/abc123")
    assert found is not None
    assert found.path_params == {"campaign_id": "abc123"}


def test_the_method_is_part_of_the_match() -> None:
    assert match(ROUTES, "GET", "/campaigns") is None
    assert match(ROUTES, "POST", "/campaigns") is not None


def test_an_unknown_path_does_not_match() -> None:
    assert match(ROUTES, "GET", "/nope") is None
    assert match(ROUTES, "GET", "/campaigns/abc/extra") is None


def test_a_query_string_is_parsed_and_never_part_of_the_path_match() -> None:
    found = match(ROUTES, "GET", "/campaigns/abc123?verbose=1&page=2")
    assert found is not None
    assert found.path_params == {"campaign_id": "abc123"}
    assert found.query_params == {"verbose": "1", "page": "2"}


def test_a_percent_encoded_parameter_is_decoded() -> None:
    found = match(ROUTES, "GET", "/r/summer%20sale")
    assert found is not None
    assert found.path_params == {"slug": "summer sale"}


def test_split_separates_path_from_query() -> None:
    assert split("/r/promo?a=1") == ("/r/promo", {"a": "1"})
    assert split("/r/promo") == ("/r/promo", {})
