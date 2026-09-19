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
class FakeSpeechApplicationClient(client.SpeechApplicationClient, client.InterpretationApplicationClient):
    async def speak_turn(self, speak_turn_request: relays.SpeakTurnRequest) -> relays.SpeakTurnResponse:
        return relays.SpeakTurnResponse(call_id=str(speak_turn_request.call.identity), text="hi")

    async def interpret_turn(self, interpret_turn_request: relays.InterpretTurnRequest) -> relays.InterpretTurnResponse:
        return relays.InterpretTurnResponse(call_id=str(interpret_turn_request.call.identity), person_names=("Grace",))


@ts.fake
class FakeRestateWorkflowContext:  # tesser:debt TB072
    def __init__(self) -> None:
        self.called: list[tuple[object, object]] = []

    async def service_call(self, tpe: object, arg: object) -> object:
        self.called.append((tpe, arg))
        return relays.InterpretTurnResponse(call_id="c1", person_names=("Grace",))


@ts.helper
def call_spec(call_id: str = "c1", name: str = "Ada", phone_number: str = "+15555550100") -> domain.CallSpec:
    return domain.CallSpec(
        call_id=call_id, person=domain.PersonSpec(name=name, phone_number=phone_number), turns=(), step="ask_name"
    )


class TestRestateInvocationInterpretationRelay:
    async def test_running_interpret_turn_journals_a_call_to_the_runtimes_handler(self) -> None:
        restate_call_runtime = runtimes.RestateCallRuntime(
            FakeCallApplicationClient(),
            FakeDialingApplicationClient(),
            FakeSpeechApplicationClient(),
            FakeSpeechApplicationClient(),
        )
        fake_restate_workflow_context = FakeRestateWorkflowContext()  # tesser:debt TB085
        interpret_turn_request = relays.InterpretTurnRequest(call=domain.Call(call_spec()))

        await runners.RestateInvocationInterpretationRelay(
            typing.cast(restate.WorkflowContext, fake_restate_workflow_context), restate_call_runtime
        ).run_interpret_turn(interpret_turn_request)

        assert fake_restate_workflow_context.called == [
            (restate_call_runtime.interpret_turn_handler, interpret_turn_request)
        ]
