from __future__ import annotations

import asyncio
import os

import tesser.srv as ts
import livekit.agents as livekit_agents

import app as app
import srv.livekit as livekit  # tesser:debt TB060


class LivekitAgentServer(ts.Host):

    def run(self, argv: list[str]) -> int:
        voice_app = app.load()
        agent_name = os.environ["LIVEKIT_AGENT_NAME"]
        livekit_app = livekit.LivekitApp(voice_app.calls.livekit_call_runtime)
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
