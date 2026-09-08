from __future__ import annotations  # tesser:debt TB041

import json
import typing
import urllib.parse

import tesser.adapters as ts
import httpx
import restate
import restate.client

import ordering.adapters.runtimes as runtimes
import ordering.application.relays as relays  # tesser:debt TB060
import tesser.errors as errors

_RUN_TIMEOUT: typing.Final[httpx.Timeout] = httpx.Timeout(5.0, read=None)


class RestateOrderOrchestratorRunner(ts.Gateway):

    def __init__(self, ingress: str, restate_order_runtime: runtimes.RestateOrderRuntime) -> None:
        self._ingress = ingress
        self._restate_order_runtime = restate_order_runtime

    async def start_order_orchestrator(
        self, order_orchestrator_request: relays.OrderOrchestratorRequest
    ) -> relays.StartOrderOrchestratorResponse:
        key = str(order_orchestrator_request.order.identity)
        try:
            async with httpx.AsyncClient(base_url=self._ingress) as async_client:
                await restate.client.Client(async_client).workflow_send(
                    self._restate_order_runtime.order_orchestrator_handler,
                    key=urllib.parse.quote(key, safe=""),
                    arg=order_orchestrator_request,
                )
        except restate.HttpError as http_error:
            if http_error.status_code == 409:
                raise errors.DomainError(
                    errors.Kind.CONFLICT, "order_already_started", http_error.message
                ) from http_error
            raise errors.InfraError(
                f"restate ingress refused the workflow: {http_error}"
            ) from http_error
        except httpx.TransportError as transport_error:
            raise errors.InfraError(
                f"restate ingress refused the workflow: {transport_error}"
            ) from transport_error
        return relays.StartOrderOrchestratorResponse(key)

    async def run_order_orchestrator(
        self, order_orchestrator_request: relays.OrderOrchestratorRequest
    ) -> relays.OrderOrchestratorResponse:
        key = str(order_orchestrator_request.order.identity)
        try:
            async with httpx.AsyncClient(base_url=self._ingress, timeout=_RUN_TIMEOUT) as async_client:
                return await restate.client.Client(async_client).workflow_call(
                    self._restate_order_runtime.order_orchestrator_handler,
                    key=urllib.parse.quote(key, safe=""),
                    arg=order_orchestrator_request,
                )
        except restate.HttpError as http_error:
            try:
                outcome = json.loads(http_error.body or "")
            except ValueError:
                outcome = None
            if not (
                isinstance(outcome, dict)
                and isinstance(outcome.get("message"), str)
                and outcome.get("code") == http_error.status_code
            ):
                raise errors.InfraError(
                    f"restate ingress refused the workflow: {http_error}"
                ) from http_error
            match http_error.status_code:
                case 409:
                    raise errors.DomainError(
                        errors.Kind.CONFLICT, "order_already_placed", outcome["message"]
                    ) from http_error
                case 422:
                    kind = errors.Kind.VALIDATION
                case 404:
                    kind = errors.Kind.NOT_FOUND
                case _:
                    raise errors.InfraError(
                        f"the workflow ended with a status that is not the domain's: {http_error}"
                    ) from http_error
            raise errors.DomainError(kind, "order_rejected", outcome["message"]) from http_error
        except httpx.TransportError as transport_error:
            raise errors.InfraError(
                f"restate ingress refused the workflow: {transport_error}"
            ) from transport_error
