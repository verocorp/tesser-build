from __future__ import annotations

import http.client as client
import json
import os
import pathlib
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
        "SPECIFICATION_STORAGE": "memory",
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
        assert banner.startswith("specs app listening on 127.0.0.1:")
        with pytest.raises(subprocess.TimeoutExpired):
            proc.wait(timeout=1)
        proc.terminate()
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


def test_the_server_serves_the_product_specification_page_at_the_root() -> None:
    os.environ.update(SPECIFICATION_STORAGE="memory", HTTP_HOST="127.0.0.1", HTTP_PORT="0")
    specs_app = app.load()
    http_host = http.HttpHost(("127.0.0.1", 0), specs_app)
    stop = threading.Event()
    thread = threading.Thread(target=http_host.run, args=(stop,))
    thread.start()
    try:
        conn = client.HTTPConnection("127.0.0.1", http_host.port, timeout=5)
        conn.request("GET", "/")
        resp = conn.getresponse()
        body = resp.read()
        conn.close()
        assert resp.status == 200
        assert resp.getheader("Content-Type") == "text/html; charset=utf-8"
        assert b"<title>Product Specification</title>" in body
    finally:
        stop.set()
        thread.join(5)
        specs_app.close()


def test_the_server_answers_a_routed_add_story() -> None:
    os.environ.update(SPECIFICATION_STORAGE="memory", HTTP_HOST="127.0.0.1", HTTP_PORT="0")
    specs_app = app.load()
    http_host = http.HttpHost(("127.0.0.1", 0), specs_app)
    stop = threading.Event()
    thread = threading.Thread(target=http_host.run, args=(stop,))
    thread.start()
    try:
        conn = client.HTTPConnection("127.0.0.1", http_host.port, timeout=5)
        conn.request(
            "POST",
            "/jtbd/j-root/stories",
            body=json.dumps({"given": "g", "when": "w", "then": "t"}),
            headers={"Content-Type": "application/json"},
        )
        resp = conn.getresponse()
        payload = json.loads(resp.read())
        conn.close()
        assert resp.status == 201
        assert payload == {"story_id": "j-root-s0", "level": 1, "position": 0}
    finally:
        stop.set()
        thread.join(5)
        specs_app.close()


def test_the_server_answers_an_unknown_route_with_a_problem_document() -> None:
    os.environ.update(SPECIFICATION_STORAGE="memory", HTTP_HOST="127.0.0.1", HTTP_PORT="0")
    specs_app = app.load()
    http_host = http.HttpHost(("127.0.0.1", 0), specs_app)
    stop = threading.Event()
    thread = threading.Thread(target=http_host.run, args=(stop,))
    thread.start()
    try:
        conn = client.HTTPConnection("127.0.0.1", http_host.port, timeout=5)
        conn.request("GET", "/nope")
        resp = conn.getresponse()
        payload = json.loads(resp.read())
        conn.close()
        assert resp.status == 404
        assert payload == {"type": "/problems/not_found", "detail": "unknown route"}
    finally:
        stop.set()
        thread.join(5)
        specs_app.close()


def test_the_host_runs_until_its_stop_is_set() -> None:
    os.environ.update(SPECIFICATION_STORAGE="memory", HTTP_HOST="127.0.0.1", HTTP_PORT="0")
    specs_app = app.load()
    try:
        http_host = http.HttpHost(("127.0.0.1", 0), specs_app)
        stop = threading.Event()
        thread = threading.Thread(target=http_host.run, args=(stop,))
        thread.start()
        assert thread.is_alive()
        stop.set()
        thread.join(5)
        assert not thread.is_alive()
    finally:
        specs_app.close()
