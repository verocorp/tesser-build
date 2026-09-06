from __future__ import annotations

import asyncio
import typing

import tesser.srv as ts
import fastapi
import hypercorn.asyncio
import hypercorn.config
import hypercorn.typing
import restate

import app as app
import ordering.adapters.handlers as handlers
import protocol as protocol
import tesser.errors as errors

_BIND: typing.Final[str] = "0.0.0.0:8000"
_RESTATE_DEPLOYMENT_PATH: typing.Final[str] = "/restate"
_JSON: typing.Final[str] = "application/json"


class HttpHost(ts.Host):

    def run(self, argv: list[str]) -> int:
        durable_execution_app = app.load()
        try:
            handler = handlers.Handler(durable_execution_app.ordering.client)
            router = fastapi.APIRouter()

            @router.post("/orders")
            async def place_order(request: fastapi.Request) -> fastapi.Response:  # tesser:debt TB023
                try:
                    http_response = await handler.place_order(
                        protocol.HttpRequest(body=await request.body())
                    )
                except protocol.BadRequest as e:
                    http_response = protocol.HttpResponse.problem(400, str(e))
                except errors.DomainError as e:
                    http_response = protocol.HttpResponse.problem(
                        errors.status_for(e.kind), e.message
                    )
                except errors.InfraError:
                    http_response = protocol.HttpResponse.problem(503, "unavailable")
                return fastapi.Response(
                    http_response.body, http_response.status_code, media_type=_JSON
                )

            api = fastapi.FastAPI()
            api.include_router(router)
            api.mount(
                _RESTATE_DEPLOYMENT_PATH,
                restate.app(
                    [
                        durable_execution_app.ordering.restate_order_runtime.order_actions_service,
                        durable_execution_app.ordering.restate_order_runtime.order_orchestrator_workflow,
                    ]
                ),
            )

            config = hypercorn.config.Config()
            config.bind = [argv[0] if argv else _BIND]
            served = typing.cast(hypercorn.typing.ASGIFramework, api)
            asyncio.run(hypercorn.asyncio.serve(served, config))
            return 0
        finally:
            durable_execution_app.close()


if __name__ == "__main__":
    ts.main(HttpHost().run)
