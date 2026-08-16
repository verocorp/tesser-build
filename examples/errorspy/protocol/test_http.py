from __future__ import annotations

import pytest

import protocol.http as http


def test_a_json_object_body_is_parsed_into_its_fields() -> None:
    assert http.json_object('{"a": 1, "b": "two"}') == {"a": 1, "b": "two"}


def test_an_empty_object_body_is_accepted() -> None:
    assert http.json_object("{}") == {}


def test_a_body_that_is_not_json_is_rejected_as_malformed() -> None:
    with pytest.raises(http.BadRequest) as ei:
        http.json_object("{not json")
    assert str(ei.value).startswith("malformed JSON: ")


def test_a_json_array_body_is_rejected_because_the_top_level_must_be_an_object() -> None:
    with pytest.raises(http.BadRequest) as ei:
        http.json_object("[1, 2]")
    assert str(ei.value) == "expected a JSON object"


def test_a_json_scalar_body_is_rejected_because_the_top_level_must_be_an_object() -> None:
    with pytest.raises(http.BadRequest) as ei:
        http.json_object("7")
    assert str(ei.value) == "expected a JSON object"


def test_an_object_field_answers_the_nested_object() -> None:
    assert http.object_field({"start": "2026-01-01"}, "window") == {"start": "2026-01-01"}


def test_a_missing_object_field_is_named_in_the_rejection() -> None:
    with pytest.raises(http.BadRequest) as ei:
        http.object_field(None, "window")
    assert str(ei.value) == "'window' must be an object"


def test_a_list_where_an_object_field_is_expected_is_rejected() -> None:
    with pytest.raises(http.BadRequest) as ei:
        http.object_field([], "window")
    assert str(ei.value) == "'window' must be an object"


def test_an_array_field_answers_the_nested_list() -> None:
    assert http.array_field([{"slug": "a"}], "links") == [{"slug": "a"}]


def test_a_missing_array_field_is_named_in_the_rejection() -> None:
    with pytest.raises(http.BadRequest) as ei:
        http.array_field(None, "links")
    assert str(ei.value) == "'links' must be an array"


def test_an_object_where_an_array_field_is_expected_is_rejected() -> None:
    with pytest.raises(http.BadRequest) as ei:
        http.array_field({}, "links")
    assert str(ei.value) == "'links' must be an array"


def test_a_string_field_answers_the_string() -> None:
    assert http.string_field("spring-sale") == "spring-sale"


def test_a_number_where_a_string_field_is_expected_is_rejected() -> None:
    with pytest.raises(http.BadRequest) as ei:
        http.string_field(7)
    assert str(ei.value) == "expected a string field"


def test_a_missing_string_field_is_rejected() -> None:
    with pytest.raises(http.BadRequest) as ei:
        http.string_field(None)
    assert str(ei.value) == "expected a string field"


def test_a_response_carries_the_status_and_body_it_was_built_with() -> None:
    resp = http.Response(201, {"id": "c1"})
    assert resp.status == 201
    assert resp.body == {"id": "c1"}


def test_two_responses_with_the_same_status_and_body_are_equal() -> None:
    assert http.Response(200, {"status": "added"}) == http.Response(200, {"status": "added"})


def test_responses_differing_in_status_are_not_equal() -> None:
    assert http.Response(200, {"id": "c1"}) != http.Response(201, {"id": "c1"})


def test_responses_differing_in_body_are_not_equal() -> None:
    assert http.Response(200, {"id": "c1"}) != http.Response(200, {"id": "c2"})
