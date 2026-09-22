from __future__ import annotations

import typing

import tesser.testing as ts
import restate

import calls.adapters.runners as runners
import calls.application.relays as relays


@ts.fake
class FakeDurablePromise:  # tesser:debt TB072
    def __init__(self, resolved: bytes) -> None:
        self._resolved = resolved

    async def value(self) -> bytes:
        return self._resolved


@ts.fake
class FakeRestateWorkflowContext:  # tesser:debt TB072
    def __init__(self, resolved: bytes) -> None:
        self._resolved = resolved
        self.promised: list[str] = []

    def promise(self, name: str, serde: object) -> FakeDurablePromise:
        self.promised.append(name)
        return FakeDurablePromise(self._resolved)


class TestRestateInvocationCallOrchestratorSignalRelay:
    async def test_awaiting_person_joined_waits_on_the_promise_named_for_the_operation(self) -> None:
        fake_restate_workflow_context = FakeRestateWorkflowContext(  # tesser:debt TB085
            relays.AwaitPersonJoinedResponseSnapshot().serialize(relays.AwaitPersonJoinedResponse(call_id="c1"))
        )

        await runners.RestateInvocationCallOrchestratorSignalRelay(
            typing.cast(restate.WorkflowContext, fake_restate_workflow_context)
        ).await_person_joined(relays.AwaitPersonJoinedRequest(call_id="c1"))

        assert fake_restate_workflow_context.promised == ["person_joined"]

    async def test_awaiting_person_joined_answers_what_resolved_the_promise(self) -> None:
        fake_restate_workflow_context = FakeRestateWorkflowContext(  # tesser:debt TB085
            relays.AwaitPersonJoinedResponseSnapshot().serialize(relays.AwaitPersonJoinedResponse(call_id="c1"))
        )

        await_person_joined_response = await runners.RestateInvocationCallOrchestratorSignalRelay(
            typing.cast(restate.WorkflowContext, fake_restate_workflow_context)
        ).await_person_joined(relays.AwaitPersonJoinedRequest(call_id="c1"))

        assert await_person_joined_response.call_id == "c1"

    async def test_awaiting_a_person_turn_waits_on_the_promise_named_for_the_operation(self) -> None:
        fake_restate_workflow_context = FakeRestateWorkflowContext(  # tesser:debt TB085
            relays.AwaitPersonTurnCompletedResponseSnapshot().serialize(
                relays.AwaitPersonTurnCompletedResponse(call_id="c1", text="Grace")
            )
        )

        await runners.RestateInvocationCallOrchestratorSignalRelay(
            typing.cast(restate.WorkflowContext, fake_restate_workflow_context)
        ).await_person_turn_completed(relays.AwaitPersonTurnCompletedRequest(call_id="c1"))

        assert fake_restate_workflow_context.promised == ["person_turn_completed"]

    async def test_awaiting_a_person_turn_answers_what_the_person_said(self) -> None:
        fake_restate_workflow_context = FakeRestateWorkflowContext(  # tesser:debt TB085
            relays.AwaitPersonTurnCompletedResponseSnapshot().serialize(
                relays.AwaitPersonTurnCompletedResponse(call_id="c1", text="my name is Grace")
            )
        )

        await_person_turn_completed_response = await runners.RestateInvocationCallOrchestratorSignalRelay(
            typing.cast(restate.WorkflowContext, fake_restate_workflow_context)
        ).await_person_turn_completed(relays.AwaitPersonTurnCompletedRequest(call_id="c1"))

        assert await_person_turn_completed_response.text == "my name is Grace"
