from __future__ import annotations

import typing

import tesser.testing as ts
import restate

import calls.adapters.runners as runners
import calls.application.relays as relays
import calls.domain as domain


@ts.fake
class FakeDurablePromise:  # tesser:debt TB072
    def __init__(self, resolved: bytes) -> None:
        self._resolved = resolved

    async def value(self) -> bytes:
        return self._resolved


@ts.fake
class FakeRestateWorkflowContext:  # tesser:debt TB072
    def __init__(self) -> None:
        self.called: list[tuple[str, str, bytes]] = []
        self.promised: list[str] = []

    async def generic_call(self, service: str, handler: str, arg: bytes) -> bytes:
        self.called.append((service, handler, arg))
        if handler == "record_call":
            return relays.RecordCallResponseSnapshot().serialize(
                relays.RecordCallResponse(
                    call_id=str(relays.RecordCallRequestSnapshot().deserialize(arg).call.identity)
                )
            )
        if handler == "dial_person":
            return relays.DialPersonResponseSnapshot().serialize(relays.DialPersonResponse(call_id="c7"))
        if handler == "hang_up":
            return relays.HangUpResponseSnapshot().serialize(relays.HangUpResponse(call_id="c7"))
        return relays.SayUtteranceResponseSnapshot().serialize(relays.SayUtteranceResponse(call_id="c7"))

    def promise(self, name: str, serde: object) -> FakeDurablePromise:
        self.promised.append(name)
        if name == "person_turn_completed":
            return FakeDurablePromise(
                relays.AwaitPersonTurnCompletedResponseSnapshot().serialize(
                    relays.AwaitPersonTurnCompletedResponse(call_id="c7", text="Grace")
                )
            )
        return FakeDurablePromise(
            relays.AwaitPersonJoinedResponseSnapshot().serialize(relays.AwaitPersonJoinedResponse(call_id="c7"))
        )


@ts.helper
def conduct_call_request() -> relays.ConductCallRequest:
    return relays.ConductCallRequest(call=domain.Call(domain.CallSpec(call_id="c7", person_name="")))


class TestRestateCallWorkflow:
    async def test_an_invocation_calls_the_service_named_for_each_relay_and_the_handler_named_for_each_operation(
        self,
    ) -> None:
        fake_restate_workflow_context = FakeRestateWorkflowContext()  # tesser:debt TB085

        async with runners.RestateCallWorkflow().invocation(
            typing.cast(restate.WorkflowContext, fake_restate_workflow_context)
        ) as call_orchestrator:
            await call_orchestrator.conduct_call(conduct_call_request())

        assert [(service, handler) for service, handler, _ in fake_restate_workflow_context.called] == [
            ("DialingActions", "dial_person"),
            ("SpeechActions", "say_utterance"),
            ("SpeechActions", "say_utterance"),
            ("DialingActions", "hang_up"),
            ("CallActions", "record_call"),
        ]

    async def test_an_invocation_waits_on_the_promises_named_for_each_await(self) -> None:
        fake_restate_workflow_context = FakeRestateWorkflowContext()  # tesser:debt TB085

        async with runners.RestateCallWorkflow().invocation(
            typing.cast(restate.WorkflowContext, fake_restate_workflow_context)
        ) as call_orchestrator:
            await call_orchestrator.conduct_call(conduct_call_request())

        assert fake_restate_workflow_context.promised == ["person_joined", "person_turn_completed"]

    async def test_what_a_promise_answers_reaches_the_call_that_is_recorded(self) -> None:
        fake_restate_workflow_context = FakeRestateWorkflowContext()  # tesser:debt TB085

        async with runners.RestateCallWorkflow().invocation(
            typing.cast(restate.WorkflowContext, fake_restate_workflow_context)
        ) as call_orchestrator:
            await call_orchestrator.conduct_call(conduct_call_request())

        recorded = fake_restate_workflow_context.called[-1][2]
        assert str(relays.RecordCallRequestSnapshot().deserialize(recorded).call.person_name) == "Grace"

    async def test_an_invocation_answers_what_the_recorded_call_answered(self) -> None:
        fake_restate_workflow_context = FakeRestateWorkflowContext()  # tesser:debt TB085

        async with runners.RestateCallWorkflow().invocation(
            typing.cast(restate.WorkflowContext, fake_restate_workflow_context)
        ) as call_orchestrator:
            conduct_call_response = await call_orchestrator.conduct_call(conduct_call_request())

        assert conduct_call_response.call_id == "c7"
