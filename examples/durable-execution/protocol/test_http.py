from __future__ import annotations

import json

import pytest

import protocol.http as http


class TestHttpRequest:

    def test_a_string_and_an_integer_field_are_read_from_the_body(self) -> None:
        request = http.HttpRequest(body=b'{"sku": "widget", "quantity": 2}')
        assert request.text("sku") == "widget"
        assert request.integer("quantity") == 2

    def test_a_missing_field_is_a_bad_request(self) -> None:
        request = http.HttpRequest(body=b"{}")
        with pytest.raises(http.BadRequest):
            request.text("sku")

    def test_a_bool_is_not_an_integer(self) -> None:
        request = http.HttpRequest(body=b'{"quantity": true}')
        with pytest.raises(http.BadRequest):
            request.integer("quantity")

    def test_malformed_json_is_a_bad_request(self) -> None:
        request = http.HttpRequest(body=b"{")
        with pytest.raises(http.BadRequest):
            request.text("sku")

    def test_a_non_object_body_is_a_bad_request(self) -> None:
        request = http.HttpRequest(body=b"[]")
        with pytest.raises(http.BadRequest):
            request.integer("quantity")


class TestHttpResponse:

    def test_a_problem_carries_its_status_and_a_json_detail(self) -> None:
        answered = http.HttpResponse.problem(503, "unavailable")
        assert answered.status_code == 503
        assert json.loads(answered.body) == {"detail": "unavailable"}
