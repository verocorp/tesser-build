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


class TestRestateInvocationCallActionsRelay:
    async def test_running_record_call_calls_the_call_actions_service_by_name(self) -> None:
        fake_restate_workflow_context = FakeRestateWorkflowContext(  # tesser:debt TB085
            relays.RecordCallResponseSnapshot().serialize(relays.RecordCallResponse(call_id="c1"))
        )
        record_call_request = relays.RecordCallRequest(call=domain.Call(call_spec()))

        await runners.RestateInvocationCallActionsRelay(
            typing.cast(restate.WorkflowContext, fake_restate_workflow_context)
        ).run_record_call(record_call_request)

        assert fake_restate_workflow_context.called == [
            ("CallActions", "record_call", relays.RecordCallRequestSnapshot().serialize(record_call_request))
        ]

    async def test_running_record_call_answers_what_the_service_answered(self) -> None:
        fake_restate_workflow_context = FakeRestateWorkflowContext(  # tesser:debt TB085
            relays.RecordCallResponseSnapshot().serialize(relays.RecordCallResponse(call_id="c1"))
        )

        record_call_response = await runners.RestateInvocationCallActionsRelay(
            typing.cast(restate.WorkflowContext, fake_restate_workflow_context)
        ).run_record_call(relays.RecordCallRequest(call=domain.Call(call_spec())))

        assert record_call_response.call_id == "c1"
