from __future__ import annotations

import typing
import urllib.parse as urllib_parse

import tesser.adapters as ts
import httpx
import restate.client as restate_client

import calls.adapters.runtimes as runtimes
import calls.application.relays as relays

_READ_TIMEOUT_SECONDS: typing.Final[float] = 30.0
_RUN_TIMEOUT: typing.Final[httpx.Timeout] = httpx.Timeout(5.0, read=_READ_TIMEOUT_SECONDS)


class RestateIngressCallEventsRelay(ts.Runner):
    def __init__(self, ingress: str, restate_call_runtime: runtimes.RestateCallRuntime) -> None:
        self._ingress = ingress
        self._restate_call_runtime = restate_call_runtime

    async def run_person_answered(
        self, person_answered_request: relays.PersonAnsweredRequest
    ) -> relays.PersonAnsweredResponse:
        async with httpx.AsyncClient(base_url=self._ingress, timeout=_RUN_TIMEOUT) as async_client:
            return await restate_client.Client(async_client).workflow_call(
                self._restate_call_runtime.person_answered_handler,
                key=urllib_parse.quote(person_answered_request.call_id, safe=""),
                arg=person_answered_request,
            )

    async def run_person_input(self, person_input_request: relays.PersonInputRequest) -> relays.PersonInputResponse:
        async with httpx.AsyncClient(base_url=self._ingress, timeout=_RUN_TIMEOUT) as async_client:
            return await restate_client.Client(async_client).object_call(
                self._restate_call_runtime.person_input_handler,
                key=urllib_parse.quote(person_input_request.call_id, safe=""),
                arg=person_input_request,
            )
