from __future__ import annotations

import asyncio
import typing

import tesser.srv as ts
import hypercorn.asyncio as hypercorn_asyncio
import hypercorn.config as hypercorn_config
import hypercorn.typing as hypercorn_typing
import restate

import app as app

_BIND: typing.Final[str] = "0.0.0.0:9080"


class RestateHost(ts.Host):

    def run(self, argv: list[str]) -> int:
        voice_app = app.load()
        config = hypercorn_config.Config()
        config.bind = [argv[0] if argv else _BIND]
        served = typing.cast(
            hypercorn_typing.ASGIFramework,
            restate.app(
                [
                    voice_app.calls.restate_call_runtime.call_actions_service,
                    voice_app.calls.restate_call_runtime.dialing_actions_service,
                    voice_app.calls.restate_call_runtime.speech_actions_service,
                    voice_app.calls.restate_call_runtime.call_orchestrator_workflow,
                    voice_app.calls.restate_call_runtime.call_utterances_object,
                ]
            ),
        )
        with asyncio.Runner() as runner:
            runner.run(voice_app.open())
            try:
                runner.run(hypercorn_asyncio.serve(served, config))
            finally:
                runner.run(voice_app.close())
        return 0


if __name__ == "__main__":
    ts.main(RestateHost().run)
