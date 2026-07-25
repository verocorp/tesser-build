from __future__ import annotations

import dataclasses

import pytest

from errors import InfraError, invalid
from httpwire import (
    MAX_BUFFERED_BODY,
    BadRequest,
    HttpRequest,
    PayloadTooLarge,
    Response,
    StreamingUnsupported,
    content_length,
    decode_body,
    json_response,
    problem,
    redirect,
    respond,
)


def test_httprequest_stays_a_faithful_http_request_object() -> None:
    fields = {f.name: f.type for f in dataclasses.fields(HttpRequest)}
    assert {"method", "path", "path_params", "query_params", "headers", "body"} <= set(fields)
    assert fields["body"] in ("bytes", bytes), "request body must stay opaque bytes, not a decoded payload"


def test_response_stays_a_faithful_http_response_object() -> None:
    fields = {f.name: f.type for f in dataclasses.fields(Response)}
    assert {"status_code", "body", "headers"} <= set(fields)
    assert fields["status_code"] in ("int", int)
    assert fields["body"] in ("bytes", bytes), "response body must stay opaque bytes, so any Content-Type is expressible"


def test_json_response_serializes_to_bytes_and_owns_its_content_type() -> None:
    resp = json_response(200, {"a": 1})
    assert isinstance(resp.body, bytes)
    assert resp.body == b'{"a": 1}'
    assert resp.headers == {"Content-Type": "application/json"}


def test_json_response_merges_extra_headers_without_dropping_content_type() -> None:
    resp = json_response(200, {"a": 1}, {"Cache-Control": "no-store"})
    assert resp.headers == {"Content-Type": "application/json", "Cache-Control": "no-store"}


def test_redirect_is_an_empty_body_plus_location() -> None:
    resp = redirect("https://ok.example/x")
    assert resp.status_code == 302
    assert resp.body == b""
    assert resp.headers == {"Location": "https://ok.example/x"}


def test_decode_body_reads_bytes_and_rejects_non_json() -> None:
    assert decode_body(b'{"x": 1}') == {"x": 1}
    assert decode_body(b"") == {}
    with pytest.raises(BadRequest):
        decode_body(b"not json")
    with pytest.raises(BadRequest):
        decode_body(b"[1, 2]")
    with pytest.raises(BadRequest):
        decode_body(b"\xff")


def test_content_length_reads_a_declared_finite_size() -> None:
    assert content_length({"Content-Length": "42"}) == 42
    assert content_length({}) == 0


def test_content_length_rejects_a_non_numeric_header_as_a_client_error() -> None:
    with pytest.raises(BadRequest):
        content_length({"Content-Length": "abc"})


def test_content_length_is_case_insensitive_like_http_headers() -> None:
    assert content_length({"content-length": "42"}) == 42
    with pytest.raises(StreamingUnsupported):
        content_length({"transfer-encoding": "chunked"})


def test_content_length_refuses_a_streaming_body() -> None:
    with pytest.raises(StreamingUnsupported):
        content_length({"Transfer-Encoding": "chunked"})


def test_content_length_refuses_an_oversized_body() -> None:
    with pytest.raises(PayloadTooLarge):
        content_length({"Content-Length": str(MAX_BUFFERED_BODY + 1)})


def test_respond_maps_each_failure_class_to_a_problem_document() -> None:
    def raising(exc: Exception) -> Response:
        def run() -> Response:
            raise exc

        return respond(run)

    assert raising(BadRequest("bad")).status_code == 400
    assert raising(PayloadTooLarge("big")).status_code == 413
    assert raising(StreamingUnsupported("stream")).status_code == 411
    assert raising(invalid("bad_amount", "must be positive")).status_code == 422
    assert raising(InfraError("down")).status_code == 503
    assert raising(RuntimeError("boom")).status_code == 500


def test_respond_never_leaks_internals_on_the_unexpected_path() -> None:
    def run() -> Response:
        raise RuntimeError("secret stack detail")

    resp = respond(run)
    assert resp.status_code == 500
    assert b"secret" not in resp.body
    assert decode_body(resp.body) == problem("internal", "unexpected error")
