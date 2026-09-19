from __future__ import annotations

import datetime
import typing

import tesser.testing as ts
import restate

import calls.adapters.runners as runners
import calls.adapters.runtimes as runtimes
import calls.application.client as client
import calls.application.relays as relays


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
class FakeDurablePromise:  # tesser:debt TB072
    def __init__(self, resolved: object) -> None:
        self._resolved = resolved

    async def value(self) -> object:
        return self._resolved


@ts.fake
class FakeAwaited:  # tesser:debt TB072
    def __init__(self, resolved: object) -> None:
        self._resolved = resolved

    def __await__(self) -> typing.Generator[None, None, object]:
        yield
        return self._resolved


@ts.fake
class FakeRestateWorkflowContext:  # tesser:debt TB072
    def __init__(self, resolved: object) -> None:
        self._resolved = resolved
        self.promised: list[str] = []
        self.sent: list[tuple[object, str, object, datetime.timedelta | None]] = []

    def promise(self, name: str, serde: object) -> FakeDurablePromise:
        self.promised.append(name)
        return FakeDurablePromise(self._resolved)

    def awakeable(self, serde: object) -> tuple[str, FakeAwaited]:
        return "sign_1", FakeAwaited(self._resolved)

    def object_send(self, tpe: object, key: str, arg: object, send_delay: datetime.timedelta | None = None) -> None:
        self.sent.append((tpe, key, arg, send_delay))


@ts.helper
def heard_utterance(call_id: str = "c1", text: str = "Ada") -> relays.AwaitPersonInputResponse:
    return relays.AwaitPersonInputResponse(call_id=call_id, kind=relays.INPUT_TURN_COMPLETED, text=text)


class TestRestateInvocationPersonRelay:
    async def test_awaiting_person_answered_waits_on_the_runtimes_promise(self) -> None:
        restate_call_runtime = runtimes.RestateCallRuntime(
            FakeCallApplicationClient(),
            FakeDialingApplicationClient(),
            FakeSpeechApplicationClient(),
            FakeSpeechApplicationClient(),
        )
        fake_restate_workflow_context = FakeRestateWorkflowContext(  # tesser:debt TB085
            relays.AwaitPersonAnsweredResponse(call_id="c1")
        )

        await runners.RestateInvocationPersonRelay(
            typing.cast(restate.WorkflowContext, fake_restate_workflow_context), restate_call_runtime
        ).await_person_answered(relays.AwaitPersonAnsweredRequest(call_id="c1"))

        assert fake_restate_workflow_context.promised == [restate_call_runtime.person_answered_promise]

    async def test_awaiting_person_answered_answers_what_resolved_the_promise(self) -> None:
        fake_restate_workflow_context = FakeRestateWorkflowContext(  # tesser:debt TB085
            relays.AwaitPersonAnsweredResponse(call_id="c1")
        )

        await_person_answered_response = await runners.RestateInvocationPersonRelay(
            typing.cast(restate.WorkflowContext, fake_restate_workflow_context),
            runtimes.RestateCallRuntime(
                FakeCallApplicationClient(),
                FakeDialingApplicationClient(),
                FakeSpeechApplicationClient(),
                FakeSpeechApplicationClient(),
            ),
        ).await_person_answered(relays.AwaitPersonAnsweredRequest(call_id="c1"))

        assert await_person_answered_response.call_id == "c1"

    async def test_awaiting_a_person_input_hands_its_awakeable_to_the_mailbox_keyed_by_the_call(self) -> None:
        restate_call_runtime = runtimes.RestateCallRuntime(
            FakeCallApplicationClient(),
            FakeDialingApplicationClient(),
            FakeSpeechApplicationClient(),
            FakeSpeechApplicationClient(),
        )
        fake_restate_workflow_context = FakeRestateWorkflowContext(heard_utterance())  # tesser:debt TB085

        await runners.RestateInvocationPersonRelay(
            typing.cast(restate.WorkflowContext, fake_restate_workflow_context), restate_call_runtime
        ).await_person_input(relays.AwaitPersonInputRequest(call_id="c1", within_seconds=8))

        assert fake_restate_workflow_context.sent[0] == (
            restate_call_runtime.take_person_input_handler,
            "c1",
            "sign_1",
            None,
        )

    async def test_awaiting_a_person_input_tells_the_mailbox_to_stop_taking_once_the_seconds_are_up(self) -> None:
        restate_call_runtime = runtimes.RestateCallRuntime(
            FakeCallApplicationClient(),
            FakeDialingApplicationClient(),
            FakeSpeechApplicationClient(),
            FakeSpeechApplicationClient(),
        )
        fake_restate_workflow_context = FakeRestateWorkflowContext(heard_utterance())  # tesser:debt TB085

        await runners.RestateInvocationPersonRelay(
            typing.cast(restate.WorkflowContext, fake_restate_workflow_context), restate_call_runtime
        ).await_person_input(relays.AwaitPersonInputRequest(call_id="c1", within_seconds=8))

        assert fake_restate_workflow_context.sent[1] == (
            restate_call_runtime.stop_taking_person_input_handler,
            "c1",
            "sign_1",
            datetime.timedelta(seconds=8),
        )

    async def test_awaiting_a_person_input_answers_what_resolved_the_awakeable(self) -> None:
        fake_restate_workflow_context = FakeRestateWorkflowContext(  # tesser:debt TB085
            heard_utterance(text="my name is Ada")
        )

        await_person_input_response = await runners.RestateInvocationPersonRelay(
            typing.cast(restate.WorkflowContext, fake_restate_workflow_context),
            runtimes.RestateCallRuntime(
                FakeCallApplicationClient(),
                FakeDialingApplicationClient(),
                FakeSpeechApplicationClient(),
                FakeSpeechApplicationClient(),
            ),
        ).await_person_input(relays.AwaitPersonInputRequest(call_id="c1", within_seconds=8))

        assert (await_person_input_response.kind, await_person_input_response.text) == (
            relays.INPUT_TURN_COMPLETED,
            "my name is Ada",
        )

    async def test_waiting_for_a_completed_turn_does_not_schedule_a_no_response_deadline(self) -> None:
        restate_call_runtime = runtimes.RestateCallRuntime(
            FakeCallApplicationClient(),
            FakeDialingApplicationClient(),
            FakeSpeechApplicationClient(),
            FakeSpeechApplicationClient(),
        )
        fake_restate_workflow_context = FakeRestateWorkflowContext(heard_utterance())  # tesser:debt TB085

        await runners.RestateInvocationPersonRelay(
            typing.cast(restate.WorkflowContext, fake_restate_workflow_context), restate_call_runtime
        ).await_person_input(relays.AwaitPersonInputRequest(call_id="c1", within_seconds=None))

        assert fake_restate_workflow_context.sent == [
            (restate_call_runtime.take_person_input_handler, "c1", "sign_1", None)
        ]
