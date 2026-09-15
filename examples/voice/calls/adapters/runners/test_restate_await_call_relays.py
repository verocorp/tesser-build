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
        return relays.RecordCallResponse(call_id=record_call_request.call_id)


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
        self.sent: list[tuple[object, str, object]] = []

    def promise(self, name: str, serde: object) -> FakeDurablePromise:
        self.promised.append(name)
        return FakeDurablePromise(self._resolved)

    def awakeable(self, serde: object) -> tuple[str, FakeAwaited]:
        return "sign_1", FakeAwaited(self._resolved)

    def object_send(self, tpe: object, key: str, arg: object) -> None:
        self.sent.append((tpe, key, arg))


class TestRestateAwaitCallRelays:

    async def test_awaiting_person_answered_waits_on_the_runtimes_promise(self) -> None:
        restate_call_runtime = runtimes.RestateCallRuntime(FakeCallApplicationClient())
        fake_restate_workflow_context = FakeRestateWorkflowContext(relays.AwaitPersonAnsweredResponse(call_id="c1"))  # tesser:debt TB085

        await runners.RestateAwaitCallRelays(
            typing.cast(restate.WorkflowContext, fake_restate_workflow_context), restate_call_runtime
        ).await_person_answered(relays.AwaitPersonAnsweredRequest(call_id="c1"))

        assert fake_restate_workflow_context.promised == [restate_call_runtime.person_answered_promise]

    async def test_awaiting_person_answered_answers_what_resolved_the_promise(self) -> None:
        fake_restate_workflow_context = FakeRestateWorkflowContext(relays.AwaitPersonAnsweredResponse(call_id="c1"))  # tesser:debt TB085

        await_person_answered_response = await runners.RestateAwaitCallRelays(
            typing.cast(restate.WorkflowContext, fake_restate_workflow_context),
            runtimes.RestateCallRuntime(FakeCallApplicationClient()),
        ).await_person_answered(relays.AwaitPersonAnsweredRequest(call_id="c1"))

        assert await_person_answered_response.call_id == "c1"

    async def test_awaiting_a_person_utterance_hands_its_awakeable_to_the_mailbox_keyed_by_the_call(self) -> None:
        restate_call_runtime = runtimes.RestateCallRuntime(FakeCallApplicationClient())
        fake_restate_workflow_context = FakeRestateWorkflowContext(  # tesser:debt TB085
            relays.AwaitPersonUtteranceResponse(call_id="c1", text="Ada")
        )

        await runners.RestateAwaitCallRelays(
            typing.cast(restate.WorkflowContext, fake_restate_workflow_context), restate_call_runtime
        ).await_person_utterance(relays.AwaitPersonUtteranceRequest(call_id="c1"))

        assert fake_restate_workflow_context.sent == [
            (restate_call_runtime.take_person_utterance_handler, "c1", "sign_1")
        ]

    async def test_awaiting_a_person_utterance_answers_what_resolved_the_awakeable(self) -> None:
        fake_restate_workflow_context = FakeRestateWorkflowContext(  # tesser:debt TB085
            relays.AwaitPersonUtteranceResponse(call_id="c1", text="my name is Ada")
        )

        await_person_utterance_response = await runners.RestateAwaitCallRelays(
            typing.cast(restate.WorkflowContext, fake_restate_workflow_context),
            runtimes.RestateCallRuntime(FakeCallApplicationClient()),
        ).await_person_utterance(relays.AwaitPersonUtteranceRequest(call_id="c1"))

        assert await_person_utterance_response.text == "my name is Ada"
