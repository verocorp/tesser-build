from __future__ import annotations

import asyncio
import typing

import tesser.srv as ts
import fastapi
import hypercorn.asyncio
import hypercorn.config
import hypercorn.typing
import restate

import app.loader as loader
import ordering.adapters.handlers.http as http_handlers
import protocol.http as protocol_http
import tesser.errors as errors

_BIND: typing.Final[str] = "0.0.0.0:8000"
_MOUNT: typing.Final[str] = "/restate"
_JSON: typing.Final[str] = "application/json"


class HttpHost(ts.Host):

    def run(self, argv: list[str]) -> int:
        async def serve() -> None:
            built = loader.load()
            try:
                orders = http_handlers.Handler(built.ordering.client)
                router = fastapi.APIRouter()

                @router.post("/orders")
                async def place_order(request: fastapi.Request) -> fastapi.Response:
                    try:
                        placed = await orders.place(protocol_http.HttpRequest(body=await request.body()))
                    except protocol_http.BadRequest as e:
                        placed = protocol_http.HttpResponse.problem(400, str(e))
                    except errors.DomainError as e:
                        placed = protocol_http.HttpResponse.problem(errors.status_for(e.kind), e.message)
                    except errors.InfraError:
                        placed = protocol_http.HttpResponse.problem(503, "unavailable")
                    return fastapi.Response(placed.body, placed.status_code, media_type=_JSON)

                api = fastapi.FastAPI()
                api.include_router(router)
                api.mount(_MOUNT, restate.app(built.ordering.handlers.definitions()))

                config = hypercorn.config.Config()
                config.bind = [argv[0] if argv else _BIND]
                served = typing.cast(hypercorn.typing.ASGIFramework, api)
                await hypercorn.asyncio.serve(served, config)
            finally:
                await built.close()

        asyncio.run(serve())
        return 0


if __name__ == "__main__":
    ts.main(HttpHost().run)
