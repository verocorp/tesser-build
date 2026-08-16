from __future__ import annotations

import pytest

from protocol.http import BadRequest, HttpRequest, HttpResponse, object_field, string_field


def test_an_empty_body_reads_as_an_empty_object() -> None:
    req = HttpRequest("POST", "/campaigns", {}, {}, {}, b"")
    assert req.json_body() == {}


def test_a_json_object_body_reads_back() -> None:
    req = HttpRequest("POST", "/campaigns", {}, {}, {}, b'{"budget_amount": "100.00"}')
    assert req.json_body() == {"budget_amount": "100.00"}


def test_a_malformed_body_is_a_bad_request() -> None:
    req = HttpRequest("POST", "/campaigns", {}, {}, {}, b"{not json")
    with pytest.raises(BadRequest) as caught:
        req.json_body()
    assert "malformed JSON" in str(caught.value)


def test_an_undecodable_body_is_a_bad_request() -> None:
    req = HttpRequest("POST", "/campaigns", {}, {}, {}, b"\xff\xfe")
    with pytest.raises(BadRequest) as caught:
        req.json_body()
    assert "malformed JSON" in str(caught.value)


def test_a_json_array_body_is_a_bad_request() -> None:
    req = HttpRequest("POST", "/campaigns", {}, {}, {}, b"[1, 2]")
    with pytest.raises(BadRequest) as caught:
        req.json_body()
    assert str(caught.value) == "expected a JSON object"


def test_a_json_scalar_body_is_a_bad_request() -> None:
    req = HttpRequest("POST", "/campaigns", {}, {}, {}, b'"a string"')
    with pytest.raises(BadRequest):
        req.json_body()


def test_a_declared_path_parameter_reads_back() -> None:
    req = HttpRequest("GET", "/r/summer", {"slug": "summer"}, {}, {}, b"")
    assert req.path_param("slug") == "summer"


def test_a_missing_path_parameter_is_a_bad_request() -> None:
    req = HttpRequest("GET", "/r/summer", {"slug": "summer"}, {}, {}, b"")
    with pytest.raises(BadRequest) as caught:
        req.path_param("campaign_id")
    assert str(caught.value) == "missing path parameter: campaign_id"


def test_an_empty_path_parameter_is_a_bad_request() -> None:
    req = HttpRequest("GET", "/r/", {"slug": ""}, {}, {}, b"")
    with pytest.raises(BadRequest):
        req.path_param("slug")


def test_a_json_response_declares_its_content_type() -> None:
    resp = HttpResponse.json(201, {"campaign_id": "c-1"})
    assert resp.status_code == 201
    assert resp.headers["Content-Type"] == "application/json"
    assert resp.json_body() == {"campaign_id": "c-1"}


def test_a_declared_content_type_is_left_alone() -> None:
    resp = HttpResponse.json(200, {}, {"content-type": "application/problem+json"})
    assert resp.headers == {"content-type": "application/problem+json"}


def test_a_problem_document_carries_its_type_and_detail() -> None:
    resp = HttpResponse.problem(422, "bad_amount", "budget must be positive")
    assert resp.status_code == 422
    assert resp.json_body() == {
        "type": "/problems/bad_amount",
        "detail": "budget must be positive",
    }


def test_a_redirect_carries_a_location_and_an_empty_body() -> None:
    resp = HttpResponse.redirect("https://ok.example/a")
    assert resp.status_code == 302
    assert resp.headers == {"Location": "https://ok.example/a"}
    assert resp.body == b""


def test_a_redirect_takes_a_declared_status() -> None:
    assert HttpResponse.redirect("https://ok.example/a", 301).status_code == 301


def test_a_redirect_target_carrying_a_control_character_is_rejected() -> None:
    for target in ("https://ok.example/a\r\nSet-Cookie: x=1", "https://ok.example/a\n", "https://ok.example/\x00"):
        with pytest.raises(BadRequest) as caught:
            HttpResponse.redirect(target)
        assert "control character" in str(caught.value)


def test_an_object_field_reads_back_and_anything_else_is_rejected() -> None:
    assert object_field({"a": 1}) == {"a": 1}
    with pytest.raises(BadRequest) as caught:
        object_field("a")
    assert str(caught.value) == "expected a JSON object field"


def test_a_string_field_reads_back_and_anything_else_is_rejected() -> None:
    assert string_field("summer") == "summer"
    with pytest.raises(BadRequest) as caught:
        string_field(7)
    assert str(caught.value) == "expected a string field"
