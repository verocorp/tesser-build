from __future__ import annotations

import inspect

import pytest

from protocol.http import BadRequest, HttpRequest, HttpResponse



def test_httprequest_stays_a_faithful_http_request_object() -> None:
    params = inspect.signature(HttpRequest.__init__).parameters
    assert {"method", "path", "path_params", "query_params", "headers", "body"} <= set(params)
    assert params["body"].annotation in ("bytes", bytes), "request body must stay opaque bytes, not a decoded payload"
    req = HttpRequest("GET", "/", {}, {}, {}, b'{"a": 1}')
    assert {"method", "path", "path_params", "query_params", "headers", "body"} <= set(vars(req))
    assert req.body == b'{"a": 1}'
    assert isinstance(req.body, bytes)
    assert req.method == "GET"
    assert req.path == "/"
    assert req.path_params == {}
    assert req.query_params == {}
    assert req.headers == {}


def test_a_request_field_has_no_default_every_construction_states_the_call() -> None:
    for params in (
        inspect.signature(HttpRequest.__init__).parameters,
        inspect.signature(HttpResponse.__init__).parameters,
    ):
        for name, param in params.items():
            if name == "self":
                continue
            assert param.default is inspect.Parameter.empty, f"{name} carries a default"


def test_response_stays_a_faithful_http_response_object() -> None:
    params = inspect.signature(HttpResponse.__init__).parameters
    assert {"status_code", "body", "headers"} <= set(params)
    assert params["status_code"].annotation in ("int", int)
    assert params["body"].annotation in ("bytes", bytes), "response body must stay opaque bytes, so any Content-Type is expressible"
    resp = HttpResponse(204, b"", {})
    assert {"status_code", "body", "headers"} <= set(vars(resp))
    assert resp.status_code == 204
    assert isinstance(resp.body, bytes)
    assert resp.headers == {}


def test_a_wire_record_refuses_rewriting_after_construction() -> None:
    req = HttpRequest("GET", "/campaigns", {}, {}, {}, b"")
    with pytest.raises(AttributeError):
        req.path = "/admin"
    with pytest.raises(AttributeError):
        setattr(req, "verdict", "allowed")
    assert req.path == "/campaigns"


def test_wire_records_regained_value_equality() -> None:
    assert HttpResponse(204, b"", {}) == HttpResponse(204, b"", {})
    assert HttpResponse(204, b"", {}) != HttpResponse(200, b"", {})
    assert HttpResponse(204, b"a", {}) != HttpResponse(204, b"b", {})
    assert HttpResponse(204, b"", {"X-A": "1"}) != HttpResponse(204, b"", {})


def test_response_json_serializes_to_bytes_and_owns_its_content_type() -> None:
    resp = HttpResponse.json(200, {"a": 1})
    assert isinstance(resp.body, bytes)
    assert resp.body == b'{"a": 1}'
    assert resp.headers == {"Content-Type": "application/json"}


def test_response_json_merges_extra_headers_without_dropping_content_type() -> None:
    resp = HttpResponse.json(200, {"a": 1}, {"Cache-Control": "no-store"})
    assert resp.headers == {"Content-Type": "application/json", "Cache-Control": "no-store"}


def test_a_redirect_is_an_empty_body_plus_location() -> None:
    resp = HttpResponse.redirect("https://ok.example/x")
    assert resp.status_code == 302
    assert resp.body == b""
    assert resp.headers == {"Location": "https://ok.example/x"}


def test_a_request_reads_its_own_json_body_and_rejects_non_json() -> None:
    assert HttpRequest("GET", "/", {}, {}, {}, b'{"x": 1}').json_body() == {"x": 1}
    assert HttpRequest("GET", "/", {}, {}, {}, b"").json_body() == {}
    with pytest.raises(BadRequest):
        HttpRequest("GET", "/", {}, {}, {}, b"not json").json_body()
    with pytest.raises(BadRequest):
        HttpRequest("GET", "/", {}, {}, {}, b"[1, 2]").json_body()
    with pytest.raises(BadRequest):
        HttpRequest("GET", "/", {}, {}, {}, b"\xff").json_body()


def test_a_request_reads_its_own_path_parameters() -> None:
    assert HttpRequest("GET", "/", {"campaign_id": "abc"}, {}, {}, b"").path_param("campaign_id") == "abc"


def test_a_missing_or_empty_path_parameter_is_a_client_error() -> None:
    with pytest.raises(BadRequest):
        HttpRequest("GET", "/", {}, {}, {}, b"").path_param("campaign_id")
    with pytest.raises(BadRequest):
        HttpRequest("GET", "/", {"campaign_id": ""}, {}, {}, b"").path_param("campaign_id")


def test_a_redirect_target_may_not_smuggle_a_header() -> None:
    with pytest.raises(BadRequest):
        HttpResponse.redirect("https://ok.example/x\r\nSet-Cookie: a=b")


def test_a_caller_supplied_content_type_replaces_rather_than_duplicates() -> None:
    resp = HttpResponse.json(200, {"a": 1}, {"content-type": "application/problem+json"})
    assert resp.headers == {"content-type": "application/problem+json"}