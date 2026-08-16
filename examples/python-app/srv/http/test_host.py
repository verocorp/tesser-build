from __future__ import annotations

import http.client
import json
import threading

import pytest

from bootstrap.bootstrap import new
from bootstrap.config import from_env
from protocol.http import BadRequest, HttpResponse, PayloadTooLarge, StreamingUnsupported
from tesser.errors import InfraError, conflict, invalid, not_found
from srv.http.host import MAX_BUFFERED_BODY, HttpHost, buffered_length, make_server, respond, routes_for


def test_a_request_without_a_declared_length_buffers_nothing() -> None:
    assert buffered_length(()) == 0
    assert buffered_length((("Host", "example"),)) == 0


def test_a_declared_length_is_the_number_of_bytes_to_buffer() -> None:
    assert buffered_length((("Content-Length", "42"),)) == 42
    assert buffered_length((("content-length", " 42 "),)) == 42


def test_two_agreeing_declarations_frame_one_body() -> None:
    assert buffered_length((("Content-Length", "7"), ("content-length", "7"))) == 7


def test_two_disagreeing_declarations_are_refused_rather_than_framed() -> None:
    with pytest.raises(BadRequest) as caught:
        buffered_length((("Content-Length", "7"), ("Content-Length", "9")))
    assert "conflicting Content-Length headers" in str(caught.value)


def test_a_declaration_that_is_not_plain_ascii_digits_is_refused() -> None:
    for raw in ("abc", "+7", "7.0", "0x10", "１２"):
        with pytest.raises(BadRequest):
            buffered_length((("Content-Length", raw),))


def test_a_body_at_the_buffer_limit_is_accepted_and_one_byte_more_is_not() -> None:
    assert buffered_length((("Content-Length", str(MAX_BUFFERED_BODY)),)) == MAX_BUFFERED_BODY
    with pytest.raises(PayloadTooLarge):
        buffered_length((("Content-Length", str(MAX_BUFFERED_BODY + 1)),))


def test_a_streaming_body_is_refused_whatever_it_declares() -> None:
    with pytest.raises(StreamingUnsupported):
        buffered_length((("Transfer-Encoding", "chunked"),))
    with pytest.raises(StreamingUnsupported):
        buffered_length((("transfer-encoding", "gzip"), ("Content-Length", "5")))


def test_a_response_passes_through_untouched() -> None:
    def run() -> HttpResponse:
        return HttpResponse.json(201, {"campaign_id": "c-1"})

    resp = respond(run)
    assert resp.status_code == 201
    assert resp.json_body() == {"campaign_id": "c-1"}


def test_each_failure_class_becomes_its_own_problem_document() -> None:
    def raising(exc: Exception) -> HttpResponse:
        def run() -> HttpResponse:
            raise exc

        return respond(run)

    assert raising(BadRequest("bad")).status_code == 400
    assert raising(PayloadTooLarge("big")).status_code == 413
    assert raising(StreamingUnsupported("stream")).status_code == 411
    assert raising(invalid("bad_amount", "must be positive")).status_code == 422
    assert raising(not_found("no_campaign", "not found")).status_code == 404
    assert raising(conflict("dup_slug", "already exists")).status_code == 409
    assert raising(InfraError("down")).status_code == 503
    assert raising(RuntimeError("boom")).status_code == 500


def test_a_domain_rejection_keeps_its_own_code_and_message() -> None:
    def run() -> HttpResponse:
        raise invalid("bad_amount", "budget must be positive")

    resp = respond(run)
    assert resp.json_body() == {
        "type": "/problems/bad_amount",
        "detail": "budget must be positive",
    }


def test_an_unexpected_failure_leaks_nothing() -> None:
    def run() -> HttpResponse:
        raise RuntimeError("secret stack detail")

    resp = respond(run)
    assert resp.status_code == 500
    assert b"secret" not in resp.body
    assert resp.json_body() == {"type": "/problems/internal", "detail": "unexpected error"}


def test_the_route_table_is_the_declared_one() -> None:
    env = {"CAMPAIGN_STORAGE": "memory", "LINKPOLICY_STORAGE": "memory"}
    app = new(from_env(env.get))
    try:
        assert [(route.method, route.pattern) for route in routes_for(app)] == [
            ("POST", "/campaigns"),
            ("POST", "/links"),
            ("POST", "/links/deactivate"),
            ("GET", "/campaigns/{campaign_id}"),
            ("GET", "/r/{slug}"),
            ("GET", "/reports/links-by-verdict"),
        ]
    finally:
        app.close()


def test_the_server_answers_a_routed_request() -> None:
    env = {"CAMPAIGN_STORAGE": "memory", "LINKPOLICY_STORAGE": "memory"}
    app = new(from_env(env.get))
    server = make_server(("127.0.0.1", 0), app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        conn = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=5)
        conn.request(
            "POST",
            "/campaigns",
            body=json.dumps({"budget": {"amount": "100.00", "currency": "USD"}}),
            headers={"Content-Type": "application/json"},
        )
        resp = conn.getresponse()
        payload = json.loads(resp.read())
        conn.close()
        assert resp.status == 201
        assert payload["budget"] == {"amount": "100.00", "currency": "USD"}
        assert payload["links"] == []
    finally:
        server.shutdown()
        server.server_close()
        thread.join(5)
        app.close()


def test_the_server_answers_an_unknown_route_with_a_problem_document() -> None:
    env = {"CAMPAIGN_STORAGE": "memory", "LINKPOLICY_STORAGE": "memory"}
    app = new(from_env(env.get))
    server = make_server(("127.0.0.1", 0), app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        conn = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=5)
        conn.request("GET", "/nope")
        resp = conn.getresponse()
        payload = json.loads(resp.read())
        conn.close()
        assert resp.status == 404
        assert payload == {"type": "/problems/not_found", "detail": "unknown route"}
    finally:
        server.shutdown()
        server.server_close()
        thread.join(5)
        app.close()


def test_the_server_refuses_a_body_it_cannot_buffer() -> None:
    env = {"CAMPAIGN_STORAGE": "memory", "LINKPOLICY_STORAGE": "memory"}
    app = new(from_env(env.get))
    server = make_server(("127.0.0.1", 0), app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        conn = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=5)
        conn.putrequest("POST", "/campaigns", skip_accept_encoding=True)
        conn.putheader("Transfer-Encoding", "chunked")
        conn.endheaders()
        resp = conn.getresponse()
        payload = json.loads(resp.read())
        conn.close()
        assert resp.status == 411
        assert payload["type"] == "/problems/length_required"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(5)
        app.close()


def test_the_host_runs_until_its_stop_is_set() -> None:
    env = {"CAMPAIGN_STORAGE": "memory", "LINKPOLICY_STORAGE": "memory"}
    app = new(from_env(env.get))
    try:
        host = HttpHost(("127.0.0.1", 0), app)
        stop = threading.Event()
        thread = threading.Thread(target=host.run, args=(stop,))
        thread.start()
        assert thread.is_alive()
        stop.set()
        thread.join(5)
        assert not thread.is_alive()
    finally:
        app.close()
