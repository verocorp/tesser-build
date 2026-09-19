from __future__ import annotations

import tesser.srv as ts
import livekit.agents as livekit_agents

import calls.adapters.runtimes as calls_runtimes


class LivekitApp(ts.Host):

    def __init__(self, livekit_call_runtime: calls_runtimes.LivekitCallRuntime) -> None:
        self._livekit_call_runtime = livekit_call_runtime

    async def accept_job(self, job_request: livekit_agents.JobRequest) -> None:
        await self._livekit_call_runtime.accept_job(job_request)

    async def start_job(self, job_context: livekit_agents.JobContext) -> None:
        await self._livekit_call_runtime.start_job(job_context)
