from __future__ import annotations

import tesser.srv as ts
import livekit.agents as livekit_agents

import calls.adapters.handlers as calls_handlers


class LivekitApp(ts.Host):

    def __init__(self, livekit_handler: calls_handlers.LivekitHandler) -> None:
        self._livekit_handler = livekit_handler

    async def accept_job(self, job_request: livekit_agents.JobRequest) -> None:
        await self._livekit_handler.accept_job(job_request)

    async def start_job(self, job_context: livekit_agents.JobContext) -> None:
        await self._livekit_handler.start_job(job_context)
