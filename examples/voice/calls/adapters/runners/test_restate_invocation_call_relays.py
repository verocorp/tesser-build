from __future__ import annotations

import typing

import tesser.testing as ts
import restate

import calls.adapters.runners as runners
import calls.adapters.runtimes as runtimes
import calls.application.client as client
import calls.application.relays as relays


@ts.fake
class FakeCallsApplicationClient(client.CallsApplicationClient):

    async def record_call(self, record_call_request: relays.RecordCallRequest) -> relays.RecordCallResponse:
        return relays.RecordCallResponse(call_id=record_call_request.call_id)


@ts.fake
class FakeRestateWorkflowContext:  # tesser:debt TB072

    def __init__(self) -> None:
        self.called: list[tuple[object, object]] = []

    async def service_call(self, tpe: object, arg: object) -> object:
        self.called.append((tpe, arg))
        return relays.RecordCallResponse(call_id="c1")


class TestRestateInvocationCallRelays:

    async def test_running_record_call_journals_a_call_to_the_runtimes_handler(self) -> None:
        restate_call_runtime = runtimes.RestateCallRuntime(FakeCallsApplicationClient())
        fake_restate_workflow_context = FakeRestateWorkflowContext()  # tesser:debt TB085
        record_call_request = relays.RecordCallRequest(call_id="c1", person_name="Ada", phone_number="+15555550100")

        await runners.RestateInvocationCallRelays(
            typing.cast(restate.WorkflowContext, fake_restate_workflow_context), restate_call_runtime
        ).run_record_call(record_call_request)

        assert fake_restate_workflow_context.called == [
            (restate_call_runtime.record_call_handler, record_call_request)
        ]
