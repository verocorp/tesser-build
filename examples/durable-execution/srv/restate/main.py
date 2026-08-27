from __future__ import annotations

import asyncio
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
ACTIONS: typing.Final[str] = "OrderingActions"
QUOTE: typing.Final[str] = "quote"
_BIND: typing.Final[str] = "127.0.0.1:9080"


class RestateHost(ts.Host):

    def run(self, argv: list[str]) -> int:
        async def serve() -> None:
            built = loader.load()
            try:
                workflow_handler = restate_handlers.WorkflowHandler(built.ordering.orchestrator)
                action_handler = restate_handlers.ActionHandler(built.ordering.actions)
                workflow = restate.Workflow(WORKFLOW)
                actions = restate.Service(ACTIONS)
                passthrough = restate.serde.BytesSerde()

                @workflow.main(name=RUN, accept="*/*", input_serde=passthrough, output_serde=passthrough)
                async def run_order(ctx: restate.WorkflowContext, body: bytes) -> bytes:
                    try:
                        response = await workflow_handler.run(durable.WorkflowRequest(key=ctx.key(), body=body))
                    except durable.BadInvocation as e:
                        raise restate.TerminalError(str(e), status_code=400) from e
                    except errors.DomainError as e:
                        raise restate.TerminalError(e.message, status_code=errors.status_for(e.kind)) from e
                    return response.body

                @actions.handler(name=QUOTE, accept="*/*", input_serde=passthrough, output_serde=passthrough)
                async def quote(ctx: restate.Context, body: bytes) -> bytes:
                    try:
                        response = action_handler.quote(durable.ActionRequest(body=body))
                    except durable.BadInvocation as e:
                        raise restate.TerminalError(str(e), status_code=400) from e
                    except errors.DomainError as e:
                        raise restate.TerminalError(e.message, status_code=errors.status_for(e.kind)) from e
                    return response.body

                config = hypercorn.config.Config()
                config.bind = [argv[0] if argv else _BIND]
                await hypercorn.asyncio.serve(restate.app([workflow, actions]), config)
            finally:
                await built.close()

        asyncio.run(serve())
        return 0


if __name__ == "__main__":
    ts.main(RestateHost().run)
