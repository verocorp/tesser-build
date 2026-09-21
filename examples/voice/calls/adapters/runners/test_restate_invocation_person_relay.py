from __future__ import annotations

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
class FakeSpeechApplicationClient(client.SpeechApplicationClient):
    async def say_utterance(
        self, say_utterance_request: relays.SayUtteranceRequest
    ) -> relays.SayUtteranceResponse:
        return relays.SayUtteranceResponse(call_id=say_utterance_request.call_id)


@ts.fake
class FakeDurablePromise:  # tesser:debt TB072
    def __init__(self, resolved: object) -> None:
        self._resolved = resolved

    async def value(self) -> object:
        return self._resolved


@ts.fake
class FakeRestateWorkflowContext:  # tesser:debt TB072
    def __init__(self, resolved: object) -> None:
        self._resolved = resolved
        self.promised: list[str] = []

    def promise(self, name: str, serde: object) -> FakeDurablePromise:
        self.promised.append(name)
        return FakeDurablePromise(self._resolved)


class TestRestateInvocationPersonRelay:
    async def test_awaiting_person_joined_waits_on_the_runtimes_promise(self) -> None:
        restate_call_runtime = runtimes.RestateCallRuntime(
            FakeCallApplicationClient(), FakeDialingApplicationClient(), FakeSpeechApplicationClient()
        )
        fake_restate_workflow_context = FakeRestateWorkflowContext(  # tesser:debt TB085
            relays.AwaitPersonJoinedResponse(call_id="c1")
        )

        await runners.RestateInvocationPersonRelay(
            typing.cast(restate.WorkflowContext, fake_restate_workflow_context), restate_call_runtime
        ).await_person_joined(relays.AwaitPersonJoinedRequest(call_id="c1"))

        assert fake_restate_workflow_context.promised == [restate_call_runtime.person_joined_promise]

    async def test_awaiting_person_joined_answers_what_resolved_the_promise(self) -> None:
        fake_restate_workflow_context = FakeRestateWorkflowContext(  # tesser:debt TB085
            relays.AwaitPersonJoinedResponse(call_id="c1")
        )

        await_person_joined_response = await runners.RestateInvocationPersonRelay(
            typing.cast(restate.WorkflowContext, fake_restate_workflow_context),
            runtimes.RestateCallRuntime(
                FakeCallApplicationClient(), FakeDialingApplicationClient(), FakeSpeechApplicationClient()
            ),
        ).await_person_joined(relays.AwaitPersonJoinedRequest(call_id="c1"))

        assert await_person_joined_response.call_id == "c1"

    async def test_awaiting_a_person_turn_waits_on_the_runtimes_promise(self) -> None:
        restate_call_runtime = runtimes.RestateCallRuntime(
            FakeCallApplicationClient(), FakeDialingApplicationClient(), FakeSpeechApplicationClient()
        )
        fake_restate_workflow_context = FakeRestateWorkflowContext(  # tesser:debt TB085
            relays.AwaitPersonTurnResponse(call_id="c1", text="Grace")
        )

        await runners.RestateInvocationPersonRelay(
            typing.cast(restate.WorkflowContext, fake_restate_workflow_context), restate_call_runtime
        ).await_person_turn(relays.AwaitPersonTurnRequest(call_id="c1"))

        assert fake_restate_workflow_context.promised == [restate_call_runtime.person_turn_promise]

    async def test_awaiting_a_person_turn_answers_what_the_person_said(self) -> None:
        fake_restate_workflow_context = FakeRestateWorkflowContext(  # tesser:debt TB085
            relays.AwaitPersonTurnResponse(call_id="c1", text="my name is Grace")
        )

        await_person_turn_response = await runners.RestateInvocationPersonRelay(
            typing.cast(restate.WorkflowContext, fake_restate_workflow_context),
            runtimes.RestateCallRuntime(
                FakeCallApplicationClient(), FakeDialingApplicationClient(), FakeSpeechApplicationClient()
            ),
        ).await_person_turn(relays.AwaitPersonTurnRequest(call_id="c1"))

        assert await_person_turn_response.text == "my name is Grace"
