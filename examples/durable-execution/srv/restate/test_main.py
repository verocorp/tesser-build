from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.request

import srv.restate.main as main


class TestRestateHost:

    def test_the_host_discovers_the_workflow_and_the_action_service(self) -> None:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        env = dict(os.environ, RESTATE_INGRESS="http://localhost:8080", PYTHONPATH=os.pathsep.join(sys.path))
        host = subprocess.Popen([sys.executable, "-m", "srv.restate.main", f"127.0.0.1:{port}"], env=env)
        try:
            request = urllib.request.Request(
                f"http://127.0.0.1:{port}/discover",
                headers={"Accept": "application/vnd.restate.endpointmanifest.v2+json"},
            )
            manifest: dict[str, object] = {}
            for _ in range(100):
                try:
                    with urllib.request.urlopen(request, timeout=1) as answer:
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
        services = manifest["services"]
        assert isinstance(services, list)
        assert {(s["name"], s["ty"]) for s in services} == {(main.WORKFLOW, "WORKFLOW"), (main.ACTIONS, "SERVICE")}
        assert {h["name"] for s in services for h in s["handlers"]} == {main.RUN, main.QUOTE}
