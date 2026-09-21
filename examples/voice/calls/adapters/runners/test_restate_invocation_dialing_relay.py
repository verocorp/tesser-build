from __future__ import annotations

import typing

import tesser.testing as ts
import restate

import calls.adapters.runners as runners
import calls.adapters.runtimes as runtimes
import calls.application.client as client
import calls.application.relays as relays
import calls.domain as domain


@ts.fake
class FakeCallApplicationClient(client.CallApplicationClient):
    async def record_call(self, record_call_request: relays.RecordCallRequest) -> relays.RecordCallResponse:
        return relays.RecordCallResponse(call_id=str(record_call_request.call.identity))


@ts.fake
class FakeDialingApplicationClient(client.DialingApplicationClient):
    async def dial_person(self, dial_person_request: relays.DialPersonRequest) -> relays.DialPersonResponse:
        return relays.DialPersonResponse(call_id=str(dial_person_request.call.identity))

    async def hang_up(self, hang_up_request: relays.HangUpRequest) -> relays.HangUpResponse:
        return relays.HangUpResponse(call_id=str(hang_up_request.call.identity))


@ts.fake
class FakeSpeechApplicationClient(client.SpeechApplicationClient):
    async def say_utterance(
        self, say_utterance_request: relays.SayUtteranceRequest
    ) -> relays.SayUtteranceResponse:
        return relays.SayUtteranceResponse(call_id=say_utterance_request.call_id)


@ts.fake
class FakeRestateWorkflowContext:  # tesser:debt TB072
    def __init__(self) -> None:
        self.called: list[tuple[object, object]] = []

    async def service_call(self, tpe: object, arg: object) -> object:
        self.called.append((tpe, arg))
        return relays.DialPersonResponse(call_id="c1")


@ts.helper
def call_spec(call_id: str = "c1", person_name: str = "") -> domain.CallSpec:
    return domain.CallSpec(call_id=call_id, person_name=person_name)


class TestRestateInvocationDialingRelay:
    async def test_running_dial_person_journals_a_call_to_the_runtimes_handler(self) -> None:
        restate_call_runtime = runtimes.RestateCallRuntime(
            FakeCallApplicationClient(), FakeDialingApplicationClient(), FakeSpeechApplicationClient()
        )
        fake_restate_workflow_context = FakeRestateWorkflowContext()  # tesser:debt TB085
        dial_person_request = relays.DialPersonRequest(call=domain.Call(call_spec()))

        await runners.RestateInvocationDialingRelay(
            typing.cast(restate.WorkflowContext, fake_restate_workflow_context), restate_call_runtime
        ).run_dial_person(dial_person_request)

        assert fake_restate_workflow_context.called == [(restate_call_runtime.dial_person_handler, dial_person_request)]

    async def test_running_hang_up_journals_a_call_to_the_runtimes_handler(self) -> None:
        restate_call_runtime = runtimes.RestateCallRuntime(
            FakeCallApplicationClient(), FakeDialingApplicationClient(), FakeSpeechApplicationClient()
        )
        fake_restate_workflow_context = FakeRestateWorkflowContext()  # tesser:debt TB085
        hang_up_request = relays.HangUpRequest(call=domain.Call(call_spec()))

        await runners.RestateInvocationDialingRelay(
            typing.cast(restate.WorkflowContext, fake_restate_workflow_context), restate_call_runtime
        ).run_hang_up(hang_up_request)

        assert fake_restate_workflow_context.called == [(restate_call_runtime.hang_up_handler, hang_up_request)]
