from __future__ import annotations

import asyncio
import os
import subprocess
import sys

import livekit.agents as livekit_agents
import livekit.agents.job as livekit_job
import livekit.protocol.agent as livekit_agent

import app
import calls.adapters.handlers as calls_handlers
import srv.livekit as livekit


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


class TestLivekitApp:

    async def test_an_sdk_job_offer_reaches_the_handler_and_accepts_its_configured_identity(self) -> None:
        voice_app = app.load()
        livekit_app = livekit.LivekitApp(
            calls_handlers.LivekitHandler(voice_app.calls.client, os.environ["LIVEKIT_AGENT_NAME"], "stt", "tts")
        )
        accepted: asyncio.Queue[livekit_job.JobAcceptArguments] = asyncio.Queue()
        rejected: asyncio.Queue[bool] = asyncio.Queue()
        job_request = livekit_agents.JobRequest(
            job=livekit_agent.Job(id="job-7"), on_accept=accepted.put, on_reject=rejected.put
        )

        await livekit_app.accept_job(job_request)

        assert accepted.get_nowait().identity == os.environ["LIVEKIT_AGENT_NAME"]
        assert rejected.empty()
