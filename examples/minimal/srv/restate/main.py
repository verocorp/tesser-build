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
        minimal_app = app.load()
        try:
            config = hypercorn_config.Config()
            config.bind = [argv[0] if argv else _BIND]
            served = typing.cast(
                hypercorn_typing.ASGIFramework,
                restate.app([minimal_app.alpha.widget_actions_service, minimal_app.alpha.widget_orchestrator_workflow]),
            )
            asyncio.run(hypercorn_asyncio.serve(served, config))
            return 0
        finally:
            minimal_app.close()


if __name__ == "__main__":
    ts.main(RestateHost().run)
