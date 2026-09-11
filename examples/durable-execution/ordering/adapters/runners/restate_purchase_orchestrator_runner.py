from __future__ import annotations

import json
import typing
import urllib.parse

import tesser.adapters as ts
import httpx
import restate
import restate.client

import ordering.adapters.runtimes as runtimes
import ordering.application.ports as ports
import ordering.application.relays as relays

_RUN_TIMEOUT: typing.Final[httpx.Timeout] = httpx.Timeout(5.0, read=None)


class RestatePurchaseOrchestratorRunner(ts.Runner):

    def __init__(self, ingress: str, restate_order_runtime: runtimes.RestateOrderRuntime) -> None:
        self._ingress = ingress
        self._restate_order_runtime = restate_order_runtime

    async def run_purchase_orchestrator(
        self, purchase_orchestrator_request: relays.PurchaseOrchestratorRequest
    ) -> relays.PurchaseOrchestratorResponse:
        key = str(purchase_orchestrator_request.order.identity)
        try:
            async with httpx.AsyncClient(base_url=self._ingress, timeout=_RUN_TIMEOUT) as async_client:
                return await restate.client.Client(async_client).workflow_call(
                    self._restate_order_runtime.purchase_orchestrator_handler,
                    key=urllib.parse.quote(key, safe=""),
                    arg=purchase_orchestrator_request,
                )
        except restate.HttpError as http_error:
            try:
                outcome = json.loads(http_error.body or "")
            except (ValueError, RecursionError):
                outcome = None
            if not (
                isinstance(outcome, dict)
                and isinstance(outcome.get("message"), str)
                and outcome.get("code") == http_error.status_code
            ):
                raise ports.EngineUnavailable(
                    f"restate ingress refused the workflow: {http_error}"
                ) from http_error
            match http_error.status_code:
                case 409:
                    raise ports.EngineConflict(outcome["message"]) from http_error
                case 422:
                    raise ports.EngineRejected(outcome["message"]) from http_error
                case 404:
                    raise ports.EngineMissing(outcome["message"]) from http_error
                case _:
                    raise ports.EngineUnavailable(
                        f"the workflow ended with a status that is not the domain's: {http_error}"
                    ) from http_error
        except httpx.TransportError as transport_error:
            raise ports.EngineUnavailable(
                f"restate ingress unreachable: {transport_error}"
            ) from transport_error
        except (ports.EngineRejected, ValueError, RecursionError) as decode_error:
            raise ports.EngineUnavailable(
                f"restate ingress answered with a body that is not the workflow's result: {decode_error}"
            ) from decode_error
