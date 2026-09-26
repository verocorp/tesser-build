from __future__ import annotations

import asyncio
import os
import typing

import tesser.srv as ts
import livekit.agents as livekit_agents

import app as app
import calls.adapters.handlers as calls_handlers

_DEFAULT_STT_MODEL: typing.Final[str] = "deepgram/nova-3"
_DEFAULT_TTS_MODEL: typing.Final[str] = "cartesia/sonic-2"


class LivekitApp(ts.Host):

    def __init__(self, livekit_handler: calls_handlers.LivekitHandler) -> None:
        self._livekit_handler = livekit_handler

    async def accept_job(self, job_request: livekit_agents.JobRequest) -> None:
        await self._livekit_handler.accept_job(job_request)

    async def start_job(self, job_context: livekit_agents.JobContext) -> None:
        await self._livekit_handler.start_job(job_context)


class LivekitAgentServer(ts.Host):

    def run(self, argv: list[str]) -> int:
        voice_app = app.load()
        agent_name = os.environ["LIVEKIT_AGENT_NAME"]
        livekit_app = LivekitApp(
            calls_handlers.LivekitHandler(
                voice_app.calls.client,
                agent_name,
                os.environ.get("LIVEKIT_STT_MODEL", _DEFAULT_STT_MODEL),
                os.environ.get("LIVEKIT_TTS_MODEL", _DEFAULT_TTS_MODEL),
            )
        )
        agent_server = livekit_agents.AgentServer(
            job_executor_type=livekit_agents.JobExecutorType.THREAD,
            ws_url=os.environ["LIVEKIT_URL"],
            api_key=os.environ["LIVEKIT_API_KEY"],
            api_secret=os.environ["LIVEKIT_API_SECRET"],
        )
        agent_server.rtc_session(
            livekit_app.start_job, agent_name=agent_name, on_request=livekit_app.accept_job
        )
        with asyncio.Runner() as runner:
            runner.run(voice_app.open())
            try:
                runner.run(agent_server.run())
            finally:
                runner.run(voice_app.close())
        return 0


if __name__ == "__main__":
    ts.main(LivekitAgentServer().run)
