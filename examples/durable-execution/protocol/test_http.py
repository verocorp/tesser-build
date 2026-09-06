from __future__ import annotations

import json

import pytest

import protocol as protocol


class TestHttpRequest:

    def test_a_string_and_an_integer_field_are_read_from_the_body(self) -> None:
        http_request = protocol.HttpRequest(body=b'{"sku": "widget", "quantity": 2}')
        assert http_request.text("sku") == "widget"
        assert http_request.integer("quantity") == 2

    def test_a_missing_field_is_a_bad_request(self) -> None:
        http_request = protocol.HttpRequest(body=b"{}")
        with pytest.raises(protocol.BadRequest):
            http_request.text("sku")

    def test_a_bool_is_not_an_integer(self) -> None:
        http_request = protocol.HttpRequest(body=b'{"quantity": true}')
        with pytest.raises(protocol.BadRequest):
            http_request.integer("quantity")

    def test_malformed_json_is_a_bad_request(self) -> None:
        http_request = protocol.HttpRequest(body=b"{")
        with pytest.raises(protocol.BadRequest):
            http_request.text("sku")

    def test_a_non_object_body_is_a_bad_request(self) -> None:
        http_request = protocol.HttpRequest(body=b"[]")
        with pytest.raises(protocol.BadRequest):
            http_request.integer("quantity")

    def test_an_integer_too_long_to_parse_is_a_bad_request(self) -> None:
        http_request = protocol.HttpRequest(body=b'{"quantity": ' + b"1" * 4400 + b"}")
        with pytest.raises(protocol.BadRequest):
            http_request.integer("quantity")
        with pytest.raises(protocol.BadRequest):
            http_request.text("sku")


class TestHttpResponse:

    def test_a_problem_carries_its_status_and_a_json_detail(self) -> None:
        http_response = protocol.HttpResponse.problem(503, "unavailable")
        assert http_response.status_code == 503
        assert json.loads(http_response.body) == {"detail": "unavailable"}
