from __future__ import annotations

import inspect

import pytest

from tesser.errors import InfraError, invalid
from protocol.http import (
    BadRequest,
    HttpRequest,
    HttpResponse,
    PayloadTooLarge,
    StreamingUnsupported,
)
from srv.http.host import MAX_BUFFERED_BODY, buffered_length, respond



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


def test_the_host_owns_the_buffering_rule() -> None:
    assert buffered_length((("Content-Length", "42"),)) == 42
    assert buffered_length(()) == 0


def test_buffered_length_rejects_a_non_numeric_header_as_a_client_error() -> None:
    with pytest.raises(BadRequest):
        buffered_length((("Content-Length", "abc"),))


def test_buffered_length_is_case_insensitive_like_http_headers() -> None:
    assert buffered_length((("content-length", "42"),)) == 42
    with pytest.raises(StreamingUnsupported):
        buffered_length((("transfer-encoding", "chunked"),))


def test_buffered_length_refuses_a_streaming_body() -> None:
    with pytest.raises(StreamingUnsupported):
        buffered_length((("Transfer-Encoding", "chunked"),))


def test_buffered_length_refuses_an_oversized_body() -> None:
    with pytest.raises(PayloadTooLarge):
        buffered_length((("Content-Length", str(MAX_BUFFERED_BODY + 1)),))


def test_buffered_length_refuses_a_negative_declaration() -> None:
    with pytest.raises(BadRequest):
        buffered_length((("Content-Length", "-1"),))


def test_a_request_reads_its_own_path_parameters() -> None:
    assert HttpRequest("GET", "/", {"campaign_id": "abc"}, {}, {}, b"").path_param("campaign_id") == "abc"


def test_a_missing_or_empty_path_parameter_is_a_client_error() -> None:
    with pytest.raises(BadRequest):
        HttpRequest("GET", "/", {}, {}, {}, b"").path_param("campaign_id")
    with pytest.raises(BadRequest):
        HttpRequest("GET", "/", {"campaign_id": ""}, {}, {}, b"").path_param("campaign_id")


def test_conflicting_content_lengths_are_refused_rather_than_framed() -> None:
    with pytest.raises(BadRequest):
        buffered_length((("Content-Length", "0"), ("Content-Length", "49")))
    assert buffered_length((("Content-Length", "7"), ("Content-Length", "7"))) == 7


def test_a_content_length_is_plain_ascii_digits_and_nothing_else() -> None:
    for raw in ("5_0", "+50", " 50 x", "0x10", "٥"):
        with pytest.raises(BadRequest):
            buffered_length((("Content-Length", raw),))


def test_any_transfer_encoding_refuses_the_body_not_only_chunked() -> None:
    with pytest.raises(StreamingUnsupported):
        buffered_length((("Transfer-Encoding", "gzip"), ("Content-Length", "5")))


def test_a_redirect_target_may_not_smuggle_a_header() -> None:
    with pytest.raises(BadRequest):
        HttpResponse.redirect("https://ok.example/x\r\nSet-Cookie: a=b")


def test_a_caller_supplied_content_type_replaces_rather_than_duplicates() -> None:
    resp = HttpResponse.json(200, {"a": 1}, {"content-type": "application/problem+json"})
    assert resp.headers == {"content-type": "application/problem+json"}


def test_the_host_maps_each_failure_class_to_a_problem_document() -> None:
    def raising(exc: Exception) -> HttpResponse:
        def run() -> HttpResponse:
            raise exc

        return respond(run)

    assert raising(BadRequest("bad")).status_code == 400
    assert raising(PayloadTooLarge("big")).status_code == 413
    assert raising(StreamingUnsupported("stream")).status_code == 411
    assert raising(invalid("bad_amount", "must be positive")).status_code == 422
    assert raising(InfraError("down")).status_code == 503
    assert raising(RuntimeError("boom")).status_code == 500


def test_the_host_never_leaks_internals_on_the_unexpected_path() -> None:
    def run() -> HttpResponse:
        raise RuntimeError("secret stack detail")

    resp = respond(run)
    assert resp.status_code == 500
    assert b"secret" not in resp.body
    assert resp.json_body() == {"type": "/problems/internal", "detail": "unexpected error"}
