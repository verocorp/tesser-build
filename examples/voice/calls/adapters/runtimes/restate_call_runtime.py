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


class RestateConductCallRequestSerde(ts.Serde, restate_serde.Serde[relays.ConductCallRequest]):

    def serialize(self, conduct_call_request: relays.ConductCallRequest | None) -> bytes:
        if conduct_call_request is None:
            return b""
        return relays.ConductCallRequestSnapshot().serialize(conduct_call_request)

    def deserialize(self, buf: bytes) -> relays.ConductCallRequest | None:
        if not buf:
            raise restate.TerminalError(_EMPTY_BODY, status_code=400)
        return relays.ConductCallRequestSnapshot().deserialize(buf)


class RestateConductCallResponseSerde(ts.Serde, restate_serde.Serde[relays.ConductCallResponse]):

    def serialize(self, conduct_call_response: relays.ConductCallResponse | None) -> bytes:
        if conduct_call_response is None:
            return b""
        return relays.ConductCallResponseSnapshot().serialize(conduct_call_response)

    def deserialize(self, buf: bytes) -> relays.ConductCallResponse | None:
        if not buf:
            raise restate.TerminalError(_EMPTY_BODY, status_code=400)
        return relays.ConductCallResponseSnapshot().deserialize(buf)


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

    def __init__(self, call_application_client: client.CallApplicationClient) -> None:
        self.call_actions_service = restate.Service("CallActions", invocation_retry_policy=_RETRY_POLICY)
        self.call_orchestrator_workflow = restate.Workflow("CallOrchestrator", invocation_retry_policy=_RETRY_POLICY)

        @self.call_actions_service.handler(
            input_serde=RestateRecordCallRequestSerde(),
            output_serde=RestateRecordCallResponseSerde(),
        )
        async def record_call(  # tesser:debt TB023
            restate_context: restate.Context, record_call_request: relays.RecordCallRequest
        ) -> relays.RecordCallResponse:
            return await call_application_client.record_call(record_call_request)

        @self.call_orchestrator_workflow.main(
            input_serde=RestateConductCallRequestSerde(),
            output_serde=RestateConductCallResponseSerde(),
        )
        async def conduct_call(  # tesser:debt TB023
            restate_workflow_context: restate.WorkflowContext, conduct_call_request: relays.ConductCallRequest
        ) -> relays.ConductCallResponse:
            return await orchestrators.CallOrchestrator(
                runners.RestateInvocationRecordCallRelay(restate_workflow_context, self)
            ).conduct_call(conduct_call_request)

        self.record_call_handler = record_call
        self.conduct_call_handler = conduct_call
