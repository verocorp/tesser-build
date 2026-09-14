from __future__ import annotations

import typing

import tesser.adapters as ts
import restate
import restate.serde as restate_serde

import calls.adapters.runners as runners
import calls.application.client as client
import calls.application.orchestrators as orchestrators
import calls.application.relays as relays

_EMPTY_BODY: typing.Final[str] = "a message crosses the engine with a body"
_RETRY_POLICY: typing.Final[restate.InvocationRetryPolicy] = restate.InvocationRetryPolicy(
    max_attempts=5, on_max_attempts="pause"
)


class RestatePlaceCallRequestSerde(ts.Serde, restate_serde.Serde[relays.PlaceCallRequest]):

    def serialize(self, place_call_request: relays.PlaceCallRequest | None) -> bytes:
        if place_call_request is None:
            return b""
        return relays.PlaceCallRequestSnapshot().serialize(place_call_request)

    def deserialize(self, buf: bytes) -> relays.PlaceCallRequest | None:
        if not buf:
            raise restate.TerminalError(_EMPTY_BODY, status_code=400)
        return relays.PlaceCallRequestSnapshot().deserialize(buf)


class RestatePlaceCallResponseSerde(ts.Serde, restate_serde.Serde[relays.PlaceCallResponse]):

    def serialize(self, place_call_response: relays.PlaceCallResponse | None) -> bytes:
        if place_call_response is None:
            return b""
        return relays.PlaceCallResponseSnapshot().serialize(place_call_response)

    def deserialize(self, buf: bytes) -> relays.PlaceCallResponse | None:
        if not buf:
            raise restate.TerminalError(_EMPTY_BODY, status_code=400)
        return relays.PlaceCallResponseSnapshot().deserialize(buf)


class RestateRecordCallRequestSerde(ts.Serde, restate_serde.Serde[relays.RecordCallRequest]):

    def serialize(self, record_call_request: relays.RecordCallRequest | None) -> bytes:
        if record_call_request is None:
            return b""
        return relays.RecordCallRequestSnapshot().serialize(record_call_request)

    def deserialize(self, buf: bytes) -> relays.RecordCallRequest | None:
        if not buf:
            raise restate.TerminalError(_EMPTY_BODY, status_code=400)
        return relays.RecordCallRequestSnapshot().deserialize(buf)


class RestateRecordCallResponseSerde(ts.Serde, restate_serde.Serde[relays.RecordCallResponse]):

    def serialize(self, record_call_response: relays.RecordCallResponse | None) -> bytes:
        if record_call_response is None:
            return b""
        return relays.RecordCallResponseSnapshot().serialize(record_call_response)

    def deserialize(self, buf: bytes) -> relays.RecordCallResponse | None:
        if not buf:
            raise restate.TerminalError(_EMPTY_BODY, status_code=400)
        return relays.RecordCallResponseSnapshot().deserialize(buf)


class RestateCallRuntime(ts.Runtime):

    def __init__(self, calls_application_client: client.CallsApplicationClient) -> None:
        self.call_actions_service = restate.Service("CallActions", invocation_retry_policy=_RETRY_POLICY)
        self.call_orchestrator_workflow = restate.Workflow("CallOrchestrator", invocation_retry_policy=_RETRY_POLICY)

        @self.call_actions_service.handler(
            input_serde=RestateRecordCallRequestSerde(),
            output_serde=RestateRecordCallResponseSerde(),
        )
        async def record_call(  # tesser:debt TB023
            restate_context: restate.Context, record_call_request: relays.RecordCallRequest
        ) -> relays.RecordCallResponse:
            return await calls_application_client.record_call(record_call_request)

        @self.call_orchestrator_workflow.main(
            input_serde=RestatePlaceCallRequestSerde(),
            output_serde=RestatePlaceCallResponseSerde(),
        )
        async def place_call(  # tesser:debt TB023
            restate_workflow_context: restate.WorkflowContext, place_call_request: relays.PlaceCallRequest
        ) -> relays.PlaceCallResponse:
            return await orchestrators.CallOrchestrator(
                runners.RestateCallActionsRunner(restate_workflow_context, self)
            ).place_call(place_call_request)

        self.record_call_handler = record_call
        self.place_call_handler = place_call
