from __future__ import annotations

import typing

import tesser.testing as ts
import restate

import calls.adapters.runtimes as runtimes
import calls.application.client as client
import calls.application.relays as relays


@ts.fake
class FakeCallsApplicationClient(client.CallsApplicationClient):

    def __init__(self) -> None:
        self.recorded: list[relays.RecordCallRequest] = []

    async def record_call(self, record_call_request: relays.RecordCallRequest) -> relays.RecordCallResponse:
        self.recorded.append(record_call_request)
        return relays.RecordCallResponse(call_id=record_call_request.call_id)


@ts.fake
class FakeRestateWorkflowContext:  # tesser:debt TB072

    async def service_call(self, tpe: object, arg: object) -> object:
        assert isinstance(arg, relays.RecordCallRequest)
        return await FakeCallsApplicationClient().record_call(arg)


class TestRestateCallRuntime:

    def test_it_registers_one_actions_service_and_one_orchestrator_workflow(self) -> None:
        restate_call_runtime = runtimes.RestateCallRuntime(FakeCallsApplicationClient())

        registered = {
            restate_call_runtime.call_actions_service.name: sorted(restate_call_runtime.call_actions_service.handlers),
            restate_call_runtime.call_orchestrator_workflow.name: sorted(
                restate_call_runtime.call_orchestrator_workflow.handlers
            ),
        }

        assert registered == {"CallActions": ["record_call"], "CallOrchestrator": ["conduct_call"]}

    def test_every_registration_declares_a_bounded_retry_policy(self) -> None:
        restate_call_runtime = runtimes.RestateCallRuntime(FakeCallsApplicationClient())

        policies = [
            restate_call_runtime.call_actions_service.invocation_retry_policy,
            restate_call_runtime.call_orchestrator_workflow.invocation_retry_policy,
        ]

        assert [(policy.max_attempts, policy.on_max_attempts) for policy in policies if policy is not None] == [
            (5, "pause"),
            (5, "pause"),
        ]

    async def test_the_record_call_handler_hands_the_request_to_the_application_client(self) -> None:
        fake_calls_application_client = FakeCallsApplicationClient()
        record_call_request = relays.RecordCallRequest(call_id="c1", person_name="Ada", phone_number="+15555550100")

        await runtimes.RestateCallRuntime(fake_calls_application_client).record_call_handler(
            typing.cast(restate.Context, None), record_call_request
        )

        assert fake_calls_application_client.recorded == [record_call_request]

    async def test_the_conduct_call_handler_runs_the_orchestrator_inside_this_invocation(self) -> None:
        conduct_call_request = relays.ConductCallRequest(call_id="c7", person_name="Ada", phone_number="+15555550100")

        conduct_call_response = await runtimes.RestateCallRuntime(FakeCallsApplicationClient()).conduct_call_handler(  # tesser:debt TB085
            typing.cast(restate.WorkflowContext, FakeRestateWorkflowContext()), conduct_call_request
        )

        assert conduct_call_response.call_id == "c7"
