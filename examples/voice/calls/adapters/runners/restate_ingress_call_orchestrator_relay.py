from __future__ import annotations

import typing
import urllib.parse as urllib_parse

import tesser.adapters as ts
import httpx
import restate.client as restate_client

import calls.application.relays as relays

_SHARED_READ_TIMEOUT_SECONDS: typing.Final[float] = 30.0
_MAIN_TIMEOUT: typing.Final[httpx.Timeout] = httpx.Timeout(5.0, read=None)
_SHARED_TIMEOUT: typing.Final[httpx.Timeout] = httpx.Timeout(5.0, read=_SHARED_READ_TIMEOUT_SECONDS)


class RestateIngressCallOrchestratorRelay(ts.Runner):

    def __init__(self, ingress: str) -> None:
        self._ingress = ingress

    async def run_conduct_call(self, conduct_call_request: relays.ConductCallRequest) -> relays.ConductCallResponse:
        async with httpx.AsyncClient(base_url=self._ingress, timeout=_MAIN_TIMEOUT) as async_client:
            return relays.ConductCallResponseSnapshot().deserialize(
                await restate_client.Client(async_client).generic_call(
                    "CallOrchestrator",
                    "conduct_call",
                    relays.ConductCallRequestSnapshot().serialize(conduct_call_request),
                    key=urllib_parse.quote(str(conduct_call_request.call.identity), safe=""),
                    headers={"content-type": "application/json"},
                )
            )

    async def run_person_joined(self, person_joined_request: relays.PersonJoinedRequest) -> relays.PersonJoinedResponse:
        async with httpx.AsyncClient(base_url=self._ingress, timeout=_SHARED_TIMEOUT) as async_client:
            return relays.PersonJoinedResponseSnapshot().deserialize(
                await restate_client.Client(async_client).generic_call(
                    "CallOrchestrator",
                    "person_joined",
                    relays.PersonJoinedRequestSnapshot().serialize(person_joined_request),
                    key=urllib_parse.quote(person_joined_request.call_id, safe=""),
                    headers={"content-type": "application/json"},
                )
            )

    async def run_person_turn_completed(
        self, person_turn_completed_request: relays.PersonTurnCompletedRequest
    ) -> relays.PersonTurnCompletedResponse:
        async with httpx.AsyncClient(base_url=self._ingress, timeout=_SHARED_TIMEOUT) as async_client:
            return relays.PersonTurnCompletedResponseSnapshot().deserialize(
                await restate_client.Client(async_client).generic_call(
                    "CallOrchestrator",
                    "person_turn_completed",
                    relays.PersonTurnCompletedRequestSnapshot().serialize(person_turn_completed_request),
                    key=urllib_parse.quote(person_turn_completed_request.call_id, safe=""),
                    headers={"content-type": "application/json"},
                )
            )
