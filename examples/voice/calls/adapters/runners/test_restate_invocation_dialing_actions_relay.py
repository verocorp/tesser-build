from __future__ import annotations

import typing

import tesser.testing as ts
import restate

import calls.adapters.runners as runners
import calls.application.relays as relays
import calls.domain as domain


@ts.fake
class FakeRestateWorkflowContext:  # tesser:debt TB072
    def __init__(self, answer: bytes) -> None:
        self._answer = answer
        self.called: list[tuple[str, str, bytes]] = []

    async def generic_call(self, service: str, handler: str, arg: bytes) -> bytes:
        self.called.append((service, handler, arg))
        return self._answer


@ts.helper
def call_spec(call_id: str = "c1", person_name: str = "") -> domain.CallSpec:
    return domain.CallSpec(call_id=call_id, person_name=person_name)


class TestRestateInvocationDialingActionsRelay:
    async def test_running_dial_person_calls_the_dialing_actions_service_by_name(self) -> None:
        fake_restate_workflow_context = FakeRestateWorkflowContext(  # tesser:debt TB085
            relays.DialPersonResponseSnapshot().serialize(relays.DialPersonResponse(call_id="c1"))
        )
        dial_person_request = relays.DialPersonRequest(call=domain.Call(call_spec()))

        await runners.RestateInvocationDialingActionsRelay(
            typing.cast(restate.WorkflowContext, fake_restate_workflow_context)
        ).run_dial_person(dial_person_request)

        assert fake_restate_workflow_context.called == [
            ("DialingActions", "dial_person", relays.DialPersonRequestSnapshot().serialize(dial_person_request))
        ]

    async def test_running_hang_up_calls_the_dialing_actions_service_by_name(self) -> None:
        fake_restate_workflow_context = FakeRestateWorkflowContext(  # tesser:debt TB085
            relays.HangUpResponseSnapshot().serialize(relays.HangUpResponse(call_id="c1"))
        )
        hang_up_request = relays.HangUpRequest(call=domain.Call(call_spec()))

        await runners.RestateInvocationDialingActionsRelay(
            typing.cast(restate.WorkflowContext, fake_restate_workflow_context)
        ).run_hang_up(hang_up_request)

        assert fake_restate_workflow_context.called == [
            ("DialingActions", "hang_up", relays.HangUpRequestSnapshot().serialize(hang_up_request))
        ]
