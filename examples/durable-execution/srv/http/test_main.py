from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

import app.loader as loader


class TestHttpHost:

    def test_the_mounted_restate_endpoint_discovers_what_the_context_declared(self) -> None:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        env = dict(os.environ, RESTATE_INGRESS="http://localhost:8080", PYTHONPATH=os.pathsep.join(sys.path))
        host = subprocess.Popen([sys.executable, "-m", "srv.http.main", f"127.0.0.1:{port}"], env=env)
        try:
            discover = urllib.request.Request(
                f"http://127.0.0.1:{port}/restate/discover",
                headers={"Accept": "application/vnd.restate.endpointmanifest.v2+json"},
            )
            manifest: dict[str, object] = {}
            for _ in range(100):
                try:
                    with urllib.request.urlopen(discover, timeout=1) as answer:
                        manifest = json.loads(answer.read())
                    break
                except OSError:
                    time.sleep(0.1)
        finally:
            host.send_signal(signal.SIGINT)
            try:
                host.wait(timeout=10)
            except subprocess.TimeoutExpired:
                host.kill()
                host.wait()
        app = loader.load()
        try:
            declared = {d.name: sorted(d.handlers) for job in app.ordering.jobs for d in job.definitions()}
        finally:
            app.close()
        services = manifest["services"]
        assert isinstance(services, list)
        assert {s["name"] for s in services} == set(declared)
        assert {s["name"]: sorted(h["name"] for h in s["handlers"]) for s in services} == declared

    def test_the_orders_route_answers_by_the_failure_it_meets(self) -> None:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        with socket.socket() as closed:
            closed.bind(("127.0.0.1", 0))
            unreachable = closed.getsockname()[1]
        env = dict(
            os.environ,
            RESTATE_INGRESS=f"http://127.0.0.1:{unreachable}",
            PYTHONPATH=os.pathsep.join(sys.path),
        )
        host = subprocess.Popen([sys.executable, "-m", "srv.http.main", f"127.0.0.1:{port}"], env=env)
        answers: list[int] = []
        try:
            for body in (
                b'{"order_id": "o1"}',
                b'{"order_id": "o1", "sku": "gadget", "quantity": 0, "note": "gift"}',
                b'{"order_id": "o1", "sku": "gadget", "quantity": 2, "note": "gift"}',
            ):
                order = urllib.request.Request(
                    f"http://127.0.0.1:{port}/orders",
                    data=body,
                    headers={"Content-Type": "application/json"},
                )
                for _ in range(100):
                    try:
                        with urllib.request.urlopen(order, timeout=5) as answer:
                            answers.append(answer.status)
                        break
                    except urllib.error.HTTPError as e:
                        answers.append(e.code)
                        break
                    except OSError:
                        time.sleep(0.1)
        finally:
            host.send_signal(signal.SIGINT)
            try:
                host.wait(timeout=10)
            except subprocess.TimeoutExpired:
                host.kill()
                host.wait()
        assert answers == [400, 422, 503]
