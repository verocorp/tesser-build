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
_PERSON_ANSWERED_PROMISE: typing.Final[str] = "person_answered"
_BUFFERED_UTTERANCES: typing.Final[str] = "buffered"
_WAITING_AWAKEABLE: typing.Final[str] = "waiting"


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


class RestatePersonAnsweredRequestSerde(ts.Serde, restate_serde.Serde[relays.PersonAnsweredRequest]):

    def serialize(self, person_answered_request: relays.PersonAnsweredRequest | None) -> bytes:
        if person_answered_request is None:
            return b""
        return relays.PersonAnsweredRequestSnapshot().serialize(person_answered_request)

    def deserialize(self, buf: bytes) -> relays.PersonAnsweredRequest | None:
        if not buf:
            raise restate.TerminalError(_EMPTY_BODY, status_code=400)
        return relays.PersonAnsweredRequestSnapshot().deserialize(buf)


class RestatePersonAnsweredResponseSerde(ts.Serde, restate_serde.Serde[relays.PersonAnsweredResponse]):

    def serialize(self, person_answered_response: relays.PersonAnsweredResponse | None) -> bytes:
        if person_answered_response is None:
            return b""
        return relays.PersonAnsweredResponseSnapshot().serialize(person_answered_response)

    def deserialize(self, buf: bytes) -> relays.PersonAnsweredResponse | None:
        if not buf:
            raise restate.TerminalError(_EMPTY_BODY, status_code=400)
        return relays.PersonAnsweredResponseSnapshot().deserialize(buf)


class RestatePersonUtteranceRequestSerde(ts.Serde, restate_serde.Serde[relays.PersonUtteranceRequest]):

    def serialize(self, person_utterance_request: relays.PersonUtteranceRequest | None) -> bytes:
        if person_utterance_request is None:
            return b""
        return relays.PersonUtteranceRequestSnapshot().serialize(person_utterance_request)

    def deserialize(self, buf: bytes) -> relays.PersonUtteranceRequest | None:
        if not buf:
            raise restate.TerminalError(_EMPTY_BODY, status_code=400)
        return relays.PersonUtteranceRequestSnapshot().deserialize(buf)


class RestatePersonUtteranceResponseSerde(ts.Serde, restate_serde.Serde[relays.PersonUtteranceResponse]):

    def serialize(self, person_utterance_response: relays.PersonUtteranceResponse | None) -> bytes:
        if person_utterance_response is None:
            return b""
        return relays.PersonUtteranceResponseSnapshot().serialize(person_utterance_response)

    def deserialize(self, buf: bytes) -> relays.PersonUtteranceResponse | None:
        if not buf:
            raise restate.TerminalError(_EMPTY_BODY, status_code=400)
        return relays.PersonUtteranceResponseSnapshot().deserialize(buf)


class RestateAwaitPersonAnsweredResponseSerde(ts.Serde, restate_serde.Serde[relays.AwaitPersonAnsweredResponse]):

    def serialize(self, await_person_answered_response: relays.AwaitPersonAnsweredResponse | None) -> bytes:
        if await_person_answered_response is None:
            return b""
        return relays.AwaitPersonAnsweredResponseSnapshot().serialize(await_person_answered_response)

    def deserialize(self, buf: bytes) -> relays.AwaitPersonAnsweredResponse | None:
        if not buf:
            raise restate.TerminalError(_EMPTY_BODY, status_code=400)
        return relays.AwaitPersonAnsweredResponseSnapshot().deserialize(buf)


class RestateAwaitPersonUtteranceResponseSerde(ts.Serde, restate_serde.Serde[relays.AwaitPersonUtteranceResponse]):

    def serialize(self, await_person_utterance_response: relays.AwaitPersonUtteranceResponse | None) -> bytes:
        if await_person_utterance_response is None:
            return b""
        return relays.AwaitPersonUtteranceResponseSnapshot().serialize(await_person_utterance_response)

    def deserialize(self, buf: bytes) -> relays.AwaitPersonUtteranceResponse | None:
        if not buf:
            raise restate.TerminalError(_EMPTY_BODY, status_code=400)
        return relays.AwaitPersonUtteranceResponseSnapshot().deserialize(buf)


class RestateCallRuntime(ts.Runtime):

    def __init__(self, call_application_client: client.CallApplicationClient) -> None:
        self.call_actions_service = restate.Service("CallActions", invocation_retry_policy=_RETRY_POLICY)
        self.call_orchestrator_workflow = restate.Workflow("CallOrchestrator", invocation_retry_policy=_RETRY_POLICY)
        self.call_utterances_object = restate.VirtualObject("CallUtterances", invocation_retry_policy=_RETRY_POLICY)
        self.person_answered_promise = _PERSON_ANSWERED_PROMISE

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
                runners.RestateInvocationCallRelays(restate_workflow_context, self)
            ).conduct_call(conduct_call_request)

        @self.call_orchestrator_workflow.handler(
            input_serde=RestatePersonAnsweredRequestSerde(),
            output_serde=RestatePersonAnsweredResponseSerde(),
        )
        async def person_answered(  # tesser:debt TB023 TB085
            restate_workflow_shared_context: restate.WorkflowSharedContext,
            person_answered_request: relays.PersonAnsweredRequest,
        ) -> relays.PersonAnsweredResponse:
            await restate_workflow_shared_context.promise(
                _PERSON_ANSWERED_PROMISE, serde=RestateAwaitPersonAnsweredResponseSerde()
            ).resolve(relays.AwaitPersonAnsweredResponse(call_id=person_answered_request.call_id))
            return relays.PersonAnsweredResponse(call_id=person_answered_request.call_id)

        @self.call_utterances_object.handler(
            input_serde=RestatePersonUtteranceRequestSerde(),
            output_serde=RestatePersonUtteranceResponseSerde(),
        )
        async def person_utterance(  # tesser:debt TB023 TB085
            restate_object_context: restate.ObjectContext, person_utterance_request: relays.PersonUtteranceRequest
        ) -> relays.PersonUtteranceResponse:
            waiting = await restate_object_context.get(_WAITING_AWAKEABLE, type_hint=str)
            if waiting is None:
                buffered = await restate_object_context.get(_BUFFERED_UTTERANCES, type_hint=list[str]) or []
                restate_object_context.set(_BUFFERED_UTTERANCES, [*buffered, person_utterance_request.text])
            else:
                restate_object_context.clear(_WAITING_AWAKEABLE)
                restate_object_context.resolve_awakeable(
                    waiting,
                    relays.AwaitPersonUtteranceResponse(
                        call_id=person_utterance_request.call_id, text=person_utterance_request.text
                    ),
                    serde=RestateAwaitPersonUtteranceResponseSerde(),
                )
            return relays.PersonUtteranceResponse(call_id=person_utterance_request.call_id)

        @self.call_utterances_object.handler()
        async def take_person_utterance(  # tesser:debt TB023
            restate_object_context: restate.ObjectContext, awakeable_id: str
        ) -> None:
            buffered = await restate_object_context.get(_BUFFERED_UTTERANCES, type_hint=list[str]) or []
            if buffered:
                restate_object_context.set(_BUFFERED_UTTERANCES, buffered[1:])
                restate_object_context.resolve_awakeable(
                    awakeable_id,
                    relays.AwaitPersonUtteranceResponse(call_id=restate_object_context.key(), text=buffered[0]),
                    serde=RestateAwaitPersonUtteranceResponseSerde(),
                )
            else:
                restate_object_context.set(_WAITING_AWAKEABLE, awakeable_id)

        self.record_call_handler = record_call
        self.conduct_call_handler = conduct_call
        self.person_answered_handler = person_answered
        self.person_utterance_handler = person_utterance
        self.take_person_utterance_handler = take_person_utterance
