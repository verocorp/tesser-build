from __future__ import annotations

import asyncio
import sys
import traceback
import typing

import tesser.srv as ts
import fastapi
import hypercorn.asyncio as hypercorn_asyncio
import hypercorn.config as hypercorn_config
import hypercorn.typing as hypercorn_typing
import restate

import app as app
import ordering.adapters.handlers as ordering_handlers
import protocol as protocol

_BIND: typing.Final[str] = "0.0.0.0:8000"
_RESTATE_DEPLOYMENT_PATH: typing.Final[str] = "/restate"
_JSON: typing.Final[str] = "application/json"


class HttpHost(ts.Host):

    def run(self, argv: list[str]) -> int:
        durable_execution_app = app.load()
        try:
            handler = ordering_handlers.Handler(durable_execution_app.ordering.client)
            router = fastapi.APIRouter()

            @router.post("/submissions")
            async def submit_order(request: fastapi.Request) -> fastapi.Response:  # tesser:debt TB023
                try:
                    http_response = await handler.submit_order(
                        protocol.HttpRequest(body=await request.body())
                    )
                except protocol.BadRequest as e:
                    http_response = protocol.HttpResponse.problem(400, str(e))
                except Exception:
                    traceback.print_exc(file=sys.stderr)
                    http_response = protocol.HttpResponse.problem(500, "unexpected error")
                return fastapi.Response(
                    http_response.body, http_response.status_code, media_type=_JSON
                )

            @router.post("/orders")
            async def place_order(request: fastapi.Request) -> fastapi.Response:  # tesser:debt TB023
                try:
                    http_response = await handler.place_order(
                        protocol.HttpRequest(body=await request.body())
                    )
                except protocol.BadRequest as e:
                    http_response = protocol.HttpResponse.problem(400, str(e))
                except Exception:
                    traceback.print_exc(file=sys.stderr)
                    http_response = protocol.HttpResponse.problem(500, "unexpected error")
                return fastapi.Response(
                    http_response.body, http_response.status_code, media_type=_JSON
                )

            @router.post("/purchases")
            async def purchase(request: fastapi.Request) -> fastapi.Response:  # tesser:debt TB023
                try:
                    http_response = await handler.purchase(
                        protocol.HttpRequest(body=await request.body())
                    )
                except protocol.BadRequest as e:
                    http_response = protocol.HttpResponse.problem(400, str(e))
                except Exception:
                    traceback.print_exc(file=sys.stderr)
                    http_response = protocol.HttpResponse.problem(500, "unexpected error")
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
                        durable_execution_app.ordering.restate_order_runtime.purchase_actions_service,
                        durable_execution_app.ordering.restate_order_runtime.purchase_orchestrator_workflow,
                    ]
                ),
            )

            config = hypercorn_config.Config()
            config.bind = [argv[0] if argv else _BIND]
            served = typing.cast(hypercorn_typing.ASGIFramework, api)
            asyncio.run(hypercorn_asyncio.serve(served, config))
            return 0
        finally:
            durable_execution_app.close()


if __name__ == "__main__":
    ts.main(HttpHost().run)
