from __future__ import annotations

import http.client as client
import json
import os
import pathlib
import signal
import socket
import subprocess
import sys
import threading

import pytest

import app as app
import srv.http as http


def test_the_edge_announces_its_address_and_exits_zero_when_signalled() -> None:
    root = pathlib.Path(__file__).resolve().parents[2]
    env = {
        "PYTHONPATH": os.pathsep.join(entry for entry in sys.path if entry),
        "PYTHONUNBUFFERED": "1",
        "CAMPAIGN_STORAGE": "memory",
        "LINKPOLICY_STORAGE": "memory",
        "HTTP_HOST": "127.0.0.1",
        "HTTP_PORT": "0",
    }
    with subprocess.Popen(
        [sys.executable, "-W", "ignore::RuntimeWarning", "-m", "srv.http.main"],
        cwd=root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ) as proc:
        assert proc.stdout is not None
        banner = proc.stdout.readline()
        assert banner.strip() == "campaign+linkpolicy app listening on 127.0.0.1:0"
        with pytest.raises(subprocess.TimeoutExpired):
            proc.wait(timeout=1)
        proc.terminate()
        stderr = proc.communicate(timeout=30)[1]
    assert proc.returncode == 0
    assert stderr == ""


def test_the_edge_exits_zero_when_interrupted() -> None:
    root = pathlib.Path(__file__).resolve().parents[2]
    env = {
        "PYTHONPATH": os.pathsep.join(entry for entry in sys.path if entry),
        "PYTHONUNBUFFERED": "1",
        "CAMPAIGN_STORAGE": "memory",
        "LINKPOLICY_STORAGE": "memory",
        "HTTP_HOST": "127.0.0.1",
        "HTTP_PORT": "0",
    }
    with subprocess.Popen(
        [sys.executable, "-W", "ignore::RuntimeWarning", "-m", "srv.http.main"],
        cwd=root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ) as proc:
        assert proc.stdout is not None
        proc.stdout.readline()
        proc.send_signal(signal.SIGINT)
        stderr = proc.communicate(timeout=30)[1]
    assert proc.returncode == 0
    assert stderr == ""


def test_the_edge_refuses_to_start_when_a_variable_is_absent() -> None:
    root = pathlib.Path(__file__).resolve().parents[2]
    env = {
        "PYTHONPATH": os.pathsep.join(entry for entry in sys.path if entry),
        "PYTHONUNBUFFERED": "1",
        "HTTP_HOST": "127.0.0.1",
        "HTTP_PORT": "0",
    }
    with subprocess.Popen(
        [sys.executable, "-W", "ignore::RuntimeWarning", "-m", "srv.http.main"],
        cwd=root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ) as proc:
        stdout, stderr = proc.communicate(timeout=30)
    assert proc.returncode != 0
    assert stdout == ""
    assert "missing_env" in stderr


def test_the_edge_refuses_to_start_on_an_unreadable_port() -> None:
    root = pathlib.Path(__file__).resolve().parents[2]
    env = {
        "PYTHONPATH": os.pathsep.join(entry for entry in sys.path if entry),
        "PYTHONUNBUFFERED": "1",
        "CAMPAIGN_STORAGE": "memory",
        "LINKPOLICY_STORAGE": "memory",
        "HTTP_HOST": "127.0.0.1",
        "HTTP_PORT": "eighty",
    }
    with subprocess.Popen(
        [sys.executable, "-W", "ignore::RuntimeWarning", "-m", "srv.http.main"],
        cwd=root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ) as proc:
        stdout, stderr = proc.communicate(timeout=30)
    assert proc.returncode != 0
    assert stdout == ""
    assert "bad_http_port" in stderr


def test_the_edge_refuses_to_start_on_an_empty_storage_coordinate() -> None:
    root = pathlib.Path(__file__).resolve().parents[2]
    env = {
        "PYTHONPATH": os.pathsep.join(entry for entry in sys.path if entry),
        "PYTHONUNBUFFERED": "1",
        "CAMPAIGN_STORAGE": "",
        "LINKPOLICY_STORAGE": "memory",
        "HTTP_HOST": "127.0.0.1",
        "HTTP_PORT": "0",
    }
    with subprocess.Popen(
        [sys.executable, "-W", "ignore::RuntimeWarning", "-m", "srv.http.main"],
        cwd=root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ) as proc:
        stdout, stderr = proc.communicate(timeout=30)
    assert proc.returncode != 0
    assert stdout == ""
    assert "missing_coordinate" in stderr




def test_the_server_answers_a_routed_request() -> None:
    python_app = app.load()
    http_host = http.HttpHost(("127.0.0.1", 0), python_app)
    stop = threading.Event()
    thread = threading.Thread(target=http_host.run, args=(stop,))
    thread.start()
    try:
        port = http_host._server.server_address[1]
        conn = client.HTTPConnection("127.0.0.1", port, timeout=5)
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
        python_app.close()


def test_the_server_answers_an_unknown_route_with_a_problem_document() -> None:
    python_app = app.load()
    http_host = http.HttpHost(("127.0.0.1", 0), python_app)
    stop = threading.Event()
    thread = threading.Thread(target=http_host.run, args=(stop,))
    thread.start()
    try:
        port = http_host._server.server_address[1]
        conn = client.HTTPConnection("127.0.0.1", port, timeout=5)
        conn.request("GET", "/nope")
        resp = conn.getresponse()
        payload = json.loads(resp.read())
        conn.close()
        assert resp.status == 404
        assert payload == {"type": "/problems/not_found", "detail": "unknown route"}
    finally:
        stop.set()
        thread.join(5)
        python_app.close()


def test_the_server_answers_a_routed_get_with_the_campaign_it_created() -> None:
    python_app = app.load()
    http_host = http.HttpHost(("127.0.0.1", 0), python_app)
    stop = threading.Event()
    thread = threading.Thread(target=http_host.run, args=(stop,))
    thread.start()
    try:
        port = http_host._server.server_address[1]
        conn = client.HTTPConnection("127.0.0.1", port, timeout=5)
        conn.request(
            "POST",
            "/campaigns",
            body=json.dumps({"budget": {"amount": "100.00", "currency": "USD"}}),
            headers={"Content-Type": "application/json"},
        )
        created = json.loads(conn.getresponse().read())
        conn.close()
        conn = client.HTTPConnection("127.0.0.1", port, timeout=5)
        conn.request("GET", f"/campaigns/{created['campaign_id']}")
        resp = conn.getresponse()
        payload = json.loads(resp.read())
        conn.close()
        assert resp.status == 200
        assert payload["campaign_id"] == created["campaign_id"]
    finally:
        stop.set()
        thread.join(5)
        python_app.close()


def test_the_server_refuses_a_streaming_body_it_cannot_buffer() -> None:
    python_app = app.load()
    http_host = http.HttpHost(("127.0.0.1", 0), python_app)
    stop = threading.Event()
    thread = threading.Thread(target=http_host.run, args=(stop,))
    thread.start()
    try:
        port = http_host._server.server_address[1]
        conn = client.HTTPConnection("127.0.0.1", port, timeout=5)
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
        python_app.close()


def test_the_server_refuses_a_declared_length_that_is_not_ascii_digits() -> None:
    python_app = app.load()
    http_host = http.HttpHost(("127.0.0.1", 0), python_app)
    stop = threading.Event()
    thread = threading.Thread(target=http_host.run, args=(stop,))
    thread.start()
    try:
        port = http_host._server.server_address[1]
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
        python_app.close()


def test_the_server_refuses_two_disagreeing_declarations_rather_than_framing_one() -> None:
    python_app = app.load()
    http_host = http.HttpHost(("127.0.0.1", 0), python_app)
    stop = threading.Event()
    thread = threading.Thread(target=http_host.run, args=(stop,))
    thread.start()
    try:
        port = http_host._server.server_address[1]
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
        python_app.close()


def test_the_server_refuses_a_body_over_the_buffer_limit() -> None:
    python_app = app.load()
    http_host = http.HttpHost(("127.0.0.1", 0), python_app)
    stop = threading.Event()
    thread = threading.Thread(target=http_host.run, args=(stop,))
    thread.start()
    try:
        port = http_host._server.server_address[1]
        oversized = str(http.MAX_BUFFERED_BODY + 1).encode("ascii")
        with socket.create_connection(("127.0.0.1", port), timeout=5) as sock:
            sock.sendall(
                b"POST /campaigns HTTP/1.1\r\nHost: x\r\nContent-Length: " + oversized + b"\r\n\r\n"
            )
            status = sock.recv(4096).split(b"\r\n")[0]
        assert b"413" in status
    finally:
        stop.set()
        thread.join(5)
        python_app.close()


def test_the_host_runs_until_its_stop_is_set() -> None:
    python_app = app.load()
    try:
        http_host = http.HttpHost(("127.0.0.1", 0), python_app)
        stop = threading.Event()
        thread = threading.Thread(target=http_host.run, args=(stop,))
        thread.start()
        assert thread.is_alive()
        stop.set()
        thread.join(5)
        assert not thread.is_alive()
    finally:
        python_app.close()
