from __future__ import annotations

import typing
import urllib.parse as urllib_parse

import tesser.adapters as ts
import httpx
import restate
import restate.client as restate_client
import restate.serde as restate_serde

import calls.adapters.workflows as workflows
import calls.application.relays as relays

_EMPTY_BODY: typing.Final[str] = "a message crosses the engine with a body"
_FOREIGN_CALL_ID: typing.Final[str] = "a message names the call its workflow is keyed by"
_ALREADY_COMPLETED: typing.Final[int] = 409
_SHARED_READ_TIMEOUT_SECONDS: typing.Final[float] = 30.0
_MAIN_TIMEOUT: typing.Final[httpx.Timeout] = httpx.Timeout(5.0, read=None)
_SHARED_TIMEOUT: typing.Final[httpx.Timeout] = httpx.Timeout(5.0, read=_SHARED_READ_TIMEOUT_SECONDS)


class RestatePersonJoinedRequestSerde(ts.Serde, restate_serde.Serde[relays.PersonJoinedRequest]):
    def serialize(self, person_joined_request: relays.PersonJoinedRequest | None) -> bytes:
        if person_joined_request is None:
            return b""
        return relays.PersonJoinedRequestSnapshot().serialize(person_joined_request)

    def deserialize(self, buf: bytes) -> relays.PersonJoinedRequest | None:
        if not buf:
            raise restate.TerminalError(_EMPTY_BODY, status_code=400)
        return relays.PersonJoinedRequestSnapshot().deserialize(buf)


class RestatePersonJoinedResponseSerde(ts.Serde, restate_serde.Serde[relays.PersonJoinedResponse]):
    def serialize(self, person_joined_response: relays.PersonJoinedResponse | None) -> bytes:
        if person_joined_response is None:
            return b""
        return relays.PersonJoinedResponseSnapshot().serialize(person_joined_response)

    def deserialize(self, buf: bytes) -> relays.PersonJoinedResponse | None:
        if not buf:
            raise restate.TerminalError(_EMPTY_BODY, status_code=400)
        return relays.PersonJoinedResponseSnapshot().deserialize(buf)


class RestatePersonJoined(ts.Dispatcher):
    def __init__(self, call_orchestrator_workflow: restate.Workflow) -> None:
        @call_orchestrator_workflow.handler(
            input_serde=RestatePersonJoinedRequestSerde(),
            output_serde=RestatePersonJoinedResponseSerde(),
        )
        async def person_joined(
            restate_workflow_shared_context: restate.WorkflowSharedContext,
            person_joined_request: relays.PersonJoinedRequest,
        ) -> relays.PersonJoinedResponse:
            call_id = restate_workflow_shared_context.key()
            if person_joined_request.call_id != call_id:
                raise restate.TerminalError(_FOREIGN_CALL_ID, status_code=400)
            try:
                await restate_workflow_shared_context.promise(
                    relays.PERSON_JOINED_PROMISE, serde=restate_serde.BytesSerde()
                ).resolve(
                    relays.AwaitPersonJoinedResponseSnapshot().serialize(relays.AwaitPersonJoinedResponse(call_id=call_id))
                )
            except restate.TerminalError as terminal_error:
                if terminal_error.status_code != _ALREADY_COMPLETED:
                    raise
            return relays.PersonJoinedResponse(call_id=call_id)

        self.handler = person_joined


class RestatePersonTurnCompletedRequestSerde(ts.Serde, restate_serde.Serde[relays.PersonTurnCompletedRequest]):
    def serialize(self, person_turn_completed_request: relays.PersonTurnCompletedRequest | None) -> bytes:
        if person_turn_completed_request is None:
            return b""
        return relays.PersonTurnCompletedRequestSnapshot().serialize(person_turn_completed_request)

    def deserialize(self, buf: bytes) -> relays.PersonTurnCompletedRequest | None:
        if not buf:
            raise restate.TerminalError(_EMPTY_BODY, status_code=400)
        return relays.PersonTurnCompletedRequestSnapshot().deserialize(buf)


class RestatePersonTurnCompletedResponseSerde(ts.Serde, restate_serde.Serde[relays.PersonTurnCompletedResponse]):
    def serialize(self, person_turn_completed_response: relays.PersonTurnCompletedResponse | None) -> bytes:
        if person_turn_completed_response is None:
            return b""
        return relays.PersonTurnCompletedResponseSnapshot().serialize(person_turn_completed_response)

    def deserialize(self, buf: bytes) -> relays.PersonTurnCompletedResponse | None:
        if not buf:
            raise restate.TerminalError(_EMPTY_BODY, status_code=400)
        return relays.PersonTurnCompletedResponseSnapshot().deserialize(buf)


class RestatePersonTurnCompleted(ts.Dispatcher):
    def __init__(self, call_orchestrator_workflow: restate.Workflow) -> None:
        @call_orchestrator_workflow.handler(
            input_serde=RestatePersonTurnCompletedRequestSerde(),
            output_serde=RestatePersonTurnCompletedResponseSerde(),
        )
        async def person_turn_completed(
            restate_workflow_shared_context: restate.WorkflowSharedContext,
            person_turn_completed_request: relays.PersonTurnCompletedRequest,
        ) -> relays.PersonTurnCompletedResponse:
            call_id = restate_workflow_shared_context.key()
            if person_turn_completed_request.call_id != call_id:
                raise restate.TerminalError(_FOREIGN_CALL_ID, status_code=400)
            try:
                await restate_workflow_shared_context.promise(
                    relays.PERSON_TURN_COMPLETED_PROMISE, serde=restate_serde.BytesSerde()
                ).resolve(
                    relays.AwaitPersonTurnCompletedResponseSnapshot().serialize(
                        relays.AwaitPersonTurnCompletedResponse(call_id=call_id, text=person_turn_completed_request.text)
                    )
                )
            except restate.TerminalError as terminal_error:
                if terminal_error.status_code != _ALREADY_COMPLETED:
                    raise
            return relays.PersonTurnCompletedResponse(call_id=call_id)

        self.handler = person_turn_completed


class RestateHttpCallOrchestratorRelay(ts.Dispatcher):
    def __init__(
        self,
        restate_url: str,
        restate_conduct_call: workflows.RestateConductCall,
        restate_person_joined: RestatePersonJoined,
        restate_person_turn_completed: RestatePersonTurnCompleted,
    ) -> None:
        self._restate_url = restate_url
        self._restate_conduct_call = restate_conduct_call
        self._restate_person_joined = restate_person_joined
        self._restate_person_turn_completed = restate_person_turn_completed

    async def run_conduct_call(self, conduct_call_request: relays.ConductCallRequest) -> relays.ConductCallResponse:
        async with httpx.AsyncClient(base_url=self._restate_url, timeout=_MAIN_TIMEOUT) as async_client:
            return await restate_client.Client(async_client).workflow_call(
                self._restate_conduct_call.handler,
                key=urllib_parse.quote(str(conduct_call_request.call.identity), safe=""),
                arg=conduct_call_request,
            )

    async def run_person_joined(self, person_joined_request: relays.PersonJoinedRequest) -> relays.PersonJoinedResponse:
        async with httpx.AsyncClient(base_url=self._restate_url, timeout=_SHARED_TIMEOUT) as async_client:
            return await restate_client.Client(async_client).workflow_call(
                self._restate_person_joined.handler,
                key=urllib_parse.quote(person_joined_request.call_id, safe=""),
                arg=person_joined_request,
            )

    async def run_person_turn_completed(
        self, person_turn_completed_request: relays.PersonTurnCompletedRequest
    ) -> relays.PersonTurnCompletedResponse:
        async with httpx.AsyncClient(base_url=self._restate_url, timeout=_SHARED_TIMEOUT) as async_client:
            return await restate_client.Client(async_client).workflow_call(
                self._restate_person_turn_completed.handler,
                key=urllib_parse.quote(person_turn_completed_request.call_id, safe=""),
                arg=person_turn_completed_request,
            )
