from __future__ import annotations

import asyncio
import collections.abc as abc
import typing

import tesser.srv as ts
import hypercorn.asyncio
import hypercorn.config
import restate
import restate.serde

import app.loader as loader
import ordering.adapters.handlers.restate as restate_handlers
import protocol.durable as durable
import tesser.errors as errors

WORKFLOW: typing.Final[str] = "Ordering"
RUN: typing.Final[str] = "run"
_BIND: typing.Final[str] = "127.0.0.1:9080"


class RestateHost(ts.Host):

    def run(self, argv: list[str]) -> int:
        built = loader.load()
        try:
            workflow = restate.Workflow(WORKFLOW)
            passthrough = restate.serde.BytesSerde()

            @workflow.main(name=RUN, accept="*/*", input_serde=passthrough, output_serde=passthrough)
            async def run_order(ctx: restate.WorkflowContext, body: bytes) -> bytes:
                async def journaled(name: str, action: abc.Callable[[], abc.Coroutine[object, object, bytes]]) -> bytes:
                    return await ctx.run_typed(name, action, restate.RunOptions(serde=passthrough))

                handler = restate_handlers.WorkflowHandler(built.ordering.workflow(journaled))
                try:
                    response = await handler.run(durable.WorkflowRequest(key=ctx.key(), body=body))
                except durable.BadInvocation as e:
                    raise restate.TerminalError(str(e), status_code=400) from e
                except errors.DomainError as e:
                    raise restate.TerminalError(e.message, status_code=errors.status_for(e.kind)) from e
                return response.body

            config = hypercorn.config.Config()
            config.bind = [argv[0] if argv else _BIND]
            asyncio.run(hypercorn.asyncio.serve(restate.app([workflow]), config))
            return 0
        finally:
            built.close()


if __name__ == "__main__":
    ts.main(RestateHost().run)
