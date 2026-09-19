from __future__ import annotations

import asyncio
import os

import livekit.agents as livekit_agents
import livekit.agents.job as livekit_job
import livekit.protocol.agent as livekit_agent

import app
import srv.livekit as livekit


class TestLivekitApp:

    async def test_an_sdk_job_offer_reaches_the_runtime_and_accepts_its_configured_identity(self) -> None:
        voice_app = app.load()
        livekit_app = livekit.LivekitApp(voice_app.calls.livekit_call_runtime)
        accepted: asyncio.Queue[livekit_job.JobAcceptArguments] = asyncio.Queue()
        rejected: asyncio.Queue[bool] = asyncio.Queue()
        job_request = livekit_agents.JobRequest(
            job=livekit_agent.Job(id="job-7"), on_accept=accepted.put, on_reject=rejected.put
        )

        await livekit_app.accept_job(job_request)

        assert accepted.get_nowait().identity == os.environ["LIVEKIT_AGENT_NAME"]
        assert rejected.empty()
