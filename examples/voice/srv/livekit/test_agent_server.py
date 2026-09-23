from __future__ import annotations

import os
import subprocess
import sys


class TestLivekitAgentServer:

    def test_the_entrypoint_loads_and_rejects_missing_configuration_before_connecting(self) -> None:
        env = dict(os.environ, PYTHONPATH=os.pathsep.join(sys.path))
        env.pop("CALLS_STORAGE", None)

        completed = subprocess.run(
            [sys.executable, "-m", "srv.livekit.agent_server"],
            env=env,
            capture_output=True,
            text=True,
            timeout=15,
        )

        assert completed.returncode != 0
        assert "CALLS_STORAGE is required" in completed.stderr
