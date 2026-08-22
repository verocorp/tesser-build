from __future__ import annotations

import http.client
import json
import socket
import threading

import app.loader as loader
from srv.http.host import MAX_BUFFERED_BODY, HttpHost


def test_the_server_answers_a_routed_request() -> None:
    app = loader.load()
    host = HttpHost(("127.0.0.1", 0), app)
    stop = threading.Event()
    thread = threading.Thread(target=host.run, args=(stop,))
    thread.start()
    try:
        port = host._server.server_address[1]
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
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
        stop.set()
        thread.join(5)
        app.close()


def test_the_server_answers_an_unknown_route_with_a_problem_document() -> None:
    app = loader.load()
    host = HttpHost(("127.0.0.1", 0), app)
    stop = threading.Event()
    thread = threading.Thread(target=host.run, args=(stop,))
    thread.start()
    try:
        port = host._server.server_address[1]
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        conn.request("GET", "/nope")
        resp = conn.getresponse()
        payload = json.loads(resp.read())
        conn.close()
        assert resp.status == 404
        assert payload == {"type": "/problems/not_found", "detail": "unknown route"}
    finally:
        stop.set()
        thread.join(5)
        app.close()


def test_the_server_answers_a_routed_get_with_the_campaign_it_created() -> None:
    app = loader.load()
    host = HttpHost(("127.0.0.1", 0), app)
    stop = threading.Event()
    thread = threading.Thread(target=host.run, args=(stop,))
    thread.start()
    try:
        port = host._server.server_address[1]
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        conn.request(
            "POST",
            "/campaigns",
            body=json.dumps({"budget": {"amount": "100.00", "currency": "USD"}}),
            headers={"Content-Type": "application/json"},
        )
        created = json.loads(conn.getresponse().read())
        conn.close()
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        conn.request("GET", f"/campaigns/{created['campaign_id']}")
        resp = conn.getresponse()
        payload = json.loads(resp.read())
        conn.close()
        assert resp.status == 200
        assert payload["campaign_id"] == created["campaign_id"]
    finally:
        stop.set()
        thread.join(5)
        app.close()


def test_the_server_refuses_a_streaming_body_it_cannot_buffer() -> None:
    app = loader.load()
    host = HttpHost(("127.0.0.1", 0), app)
    stop = threading.Event()
    thread = threading.Thread(target=host.run, args=(stop,))
    thread.start()
    try:
        port = host._server.server_address[1]
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        conn.putrequest("POST", "/campaigns", skip_accept_encoding=True)
        conn.putheader("Transfer-Encoding", "chunked")
        conn.endheaders()
        resp = conn.getresponse()
        payload = json.loads(resp.read())
        conn.close()
        assert resp.status == 411
        assert payload["type"] == "/problems/length_required"
    finally:
        stop.set()
        thread.join(5)
        app.close()


def test_the_server_refuses_a_declared_length_that_is_not_ascii_digits() -> None:
    app = loader.load()
    host = HttpHost(("127.0.0.1", 0), app)
    stop = threading.Event()
    thread = threading.Thread(target=host.run, args=(stop,))
    thread.start()
    try:
        port = host._server.server_address[1]
        for raw in (b"abc", b"+7", b"7.0", b"0x10", "１２".encode("utf-8"), b"-1"):
            with socket.create_connection(("127.0.0.1", port), timeout=5) as sock:
                sock.sendall(
                    b"POST /campaigns HTTP/1.1\r\nHost: x\r\nContent-Length: " + raw + b"\r\n\r\n"
                )
                status = sock.recv(4096).split(b"\r\n")[0]
            assert b"400" in status, raw
    finally:
        stop.set()
        thread.join(5)
        app.close()


def test_the_server_refuses_two_disagreeing_declarations_rather_than_framing_one() -> None:
    app = loader.load()
    host = HttpHost(("127.0.0.1", 0), app)
    stop = threading.Event()
    thread = threading.Thread(target=host.run, args=(stop,))
    thread.start()
    try:
        port = host._server.server_address[1]
        with socket.create_connection(("127.0.0.1", port), timeout=5) as sock:
            sock.sendall(
                b"POST /campaigns HTTP/1.1\r\nHost: x\r\n"
                b"Content-Length: 0\r\nContent-Length: 49\r\n\r\n"
            )
            status = sock.recv(4096).split(b"\r\n")[0]
        assert b"400" in status
    finally:
        stop.set()
        thread.join(5)
        app.close()


def test_the_server_refuses_a_body_over_the_buffer_limit() -> None:
    app = loader.load()
    host = HttpHost(("127.0.0.1", 0), app)
    stop = threading.Event()
    thread = threading.Thread(target=host.run, args=(stop,))
    thread.start()
    try:
        port = host._server.server_address[1]
        oversized = str(MAX_BUFFERED_BODY + 1).encode("ascii")
        with socket.create_connection(("127.0.0.1", port), timeout=5) as sock:
            sock.sendall(
                b"POST /campaigns HTTP/1.1\r\nHost: x\r\nContent-Length: " + oversized + b"\r\n\r\n"
            )
            status = sock.recv(4096).split(b"\r\n")[0]
        assert b"413" in status
    finally:
        stop.set()
        thread.join(5)
        app.close()


def test_the_host_runs_until_its_stop_is_set() -> None:
    app = loader.load()
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
