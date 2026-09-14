from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.request as urllib_request


class TestRestateHost:

    def test_the_served_restate_endpoint_discovers_the_actions_service_and_the_orchestrator_workflow(self) -> None:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        env = dict(os.environ, PYTHONPATH=os.pathsep.join(sys.path))
        host = subprocess.Popen([sys.executable, "-m", "srv.restate.main", f"127.0.0.1:{port}"], env=env)
        discover = urllib_request.Request(
            f"http://127.0.0.1:{port}/discover",
            headers={"Accept": "application/vnd.restate.endpointmanifest.v4+json"},
        )

        manifest: dict[str, object] = {}
        for _ in range(100):
            try:
                with urllib_request.urlopen(discover, timeout=1) as answer:
                    manifest = json.loads(answer.read())
                break
            except OSError:
                time.sleep(0.1)
        host.send_signal(signal.SIGINT)
        try:
            host.wait(timeout=10)
        except subprocess.TimeoutExpired:
            host.kill()
            host.wait()

        services = manifest["services"]
        assert isinstance(services, list)
        assert {s["name"]: sorted(h["name"] for h in s["handlers"]) for s in services} == {
            "CallActions": ["record_call"],
            "CallOrchestrator": ["conduct_call"],
        }
