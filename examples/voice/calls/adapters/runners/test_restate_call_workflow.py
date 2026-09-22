from __future__ import annotations

import typing

import tesser.testing as ts
import restate

import calls.adapters.runners as runners
import calls.application.client as client
import calls.application.relays as relays
import calls.domain as domain


@ts.fake
class FakeDurablePromise:  # tesser:debt TB072
    def __init__(self, resolved: bytes) -> None:
        self._resolved = resolved

    async def value(self) -> bytes:
        return self._resolved


@ts.fake
class FakeRestateWorkflowContext:  # tesser:debt TB072
    def __init__(self, answer: bytes) -> None:
        self._answer = answer
        self.called: list[tuple[str, str, bytes]] = []
        self.promised: list[str] = []

    async def generic_call(self, service: str, handler: str, arg: bytes) -> bytes:
        self.called.append((service, handler, arg))
        return self._answer

    def promise(self, name: str, serde: object) -> FakeDurablePromise:
        self.promised.append(name)
        return FakeDurablePromise(self._answer)


@ts.fake
class FakeCallOrchestratorApplicationClient(client.CallOrchestratorApplicationClient):
    async def conduct_call(self, conduct_call_request: relays.ConductCallRequest) -> relays.ConductCallResponse:
        return relays.ConductCallResponse(call_id=str(conduct_call_request.call.identity))


@ts.fake
class FakeCallOrchestratorFactory(client.CallOrchestratorFactory):
    def __init__(self, fake_call_orchestrator_application_client: FakeCallOrchestratorApplicationClient) -> None:
        self._fake_call_orchestrator_application_client = fake_call_orchestrator_application_client
        self.built: list[
            tuple[
                relays.DialingActionsRelay,
                relays.CallOrchestratorSignalRelay,
                relays.SpeechActionsRelay,
                relays.CallActionsRelay,
            ]
        ] = []

    def __call__(
        self,
        dialing_actions_relay: relays.DialingActionsRelay,
        call_orchestrator_signal_relay: relays.CallOrchestratorSignalRelay,
        speech_actions_relay: relays.SpeechActionsRelay,
        call_actions_relay: relays.CallActionsRelay,
        /,
    ) -> client.CallOrchestratorApplicationClient:
        self.built.append((dialing_actions_relay, call_orchestrator_signal_relay, speech_actions_relay, call_actions_relay))
        return self._fake_call_orchestrator_application_client


@ts.helper
def call_spec() -> domain.CallSpec:
    return domain.CallSpec(call_id="c7", person_name="")


class TestRestateCallWorkflow:
    async def test_an_invocation_yields_what_the_factory_built(self) -> None:
        fake_call_orchestrator_application_client = FakeCallOrchestratorApplicationClient()

        async with runners.RestateCallWorkflow(
            FakeCallOrchestratorFactory(fake_call_orchestrator_application_client)
        ).invocation(typing.cast(restate.WorkflowContext, FakeRestateWorkflowContext(b""))) as call_orchestrator_application_client:
            assert call_orchestrator_application_client is fake_call_orchestrator_application_client

    async def test_the_factory_is_handed_relays_that_call_the_services_named_for_them_on_this_invocation(
        self,
    ) -> None:
        fake_restate_workflow_context = FakeRestateWorkflowContext(  # tesser:debt TB085
            relays.RecordCallResponseSnapshot().serialize(relays.RecordCallResponse(call_id="c7"))
        )
        fake_call_orchestrator_factory = FakeCallOrchestratorFactory(FakeCallOrchestratorApplicationClient())
        record_call_request = relays.RecordCallRequest(call=domain.Call(call_spec()))

        async with runners.RestateCallWorkflow(fake_call_orchestrator_factory).invocation(
            typing.cast(restate.WorkflowContext, fake_restate_workflow_context)
        ):
            record_call_response = await fake_call_orchestrator_factory.built[0][3].run_record_call(record_call_request)

        assert fake_restate_workflow_context.called == [
            ("CallActions", "record_call", relays.RecordCallRequestSnapshot().serialize(record_call_request))
        ]
        assert record_call_response.call_id == "c7"

    async def test_the_dialing_relay_calls_dialing_actions_by_operation(self) -> None:
        fake_restate_workflow_context = FakeRestateWorkflowContext(  # tesser:debt TB085
            relays.DialPersonResponseSnapshot().serialize(relays.DialPersonResponse(call_id="c7"))
        )
        fake_call_orchestrator_factory = FakeCallOrchestratorFactory(FakeCallOrchestratorApplicationClient())

        async with runners.RestateCallWorkflow(fake_call_orchestrator_factory).invocation(
            typing.cast(restate.WorkflowContext, fake_restate_workflow_context)
        ):
            await fake_call_orchestrator_factory.built[0][0].run_dial_person(relays.DialPersonRequest(call=domain.Call(call_spec())))
            await fake_call_orchestrator_factory.built[0][0].run_hang_up(relays.HangUpRequest(call=domain.Call(call_spec())))

        assert [(service, handler) for service, handler, _ in fake_restate_workflow_context.called] == [
            ("DialingActions", "dial_person"),
            ("DialingActions", "hang_up"),
        ]

    async def test_the_speech_relay_calls_speech_actions_by_operation(self) -> None:
        fake_restate_workflow_context = FakeRestateWorkflowContext(  # tesser:debt TB085
            relays.SayUtteranceResponseSnapshot().serialize(relays.SayUtteranceResponse(call_id="c7"))
        )
        fake_call_orchestrator_factory = FakeCallOrchestratorFactory(FakeCallOrchestratorApplicationClient())
        say_utterance_request = relays.SayUtteranceRequest(call_id="c7", text="Hello.")

        async with runners.RestateCallWorkflow(fake_call_orchestrator_factory).invocation(
            typing.cast(restate.WorkflowContext, fake_restate_workflow_context)
        ):
            await fake_call_orchestrator_factory.built[0][2].run_say_utterance(say_utterance_request)

        assert fake_restate_workflow_context.called == [
            ("SpeechActions", "say_utterance", relays.SayUtteranceRequestSnapshot().serialize(say_utterance_request))
        ]

    async def test_the_signal_relay_waits_on_the_promise_named_for_each_await_and_answers_it(self) -> None:
        fake_restate_workflow_context = FakeRestateWorkflowContext(  # tesser:debt TB085
            relays.AwaitPersonTurnCompletedResponseSnapshot().serialize(
                relays.AwaitPersonTurnCompletedResponse(call_id="c7", text="Grace")
            )
        )
        fake_call_orchestrator_factory = FakeCallOrchestratorFactory(FakeCallOrchestratorApplicationClient())

        async with runners.RestateCallWorkflow(fake_call_orchestrator_factory).invocation(
            typing.cast(restate.WorkflowContext, fake_restate_workflow_context)
        ):
            await_person_turn_completed_response = await fake_call_orchestrator_factory.built[0][
                1
            ].await_person_turn_completed(relays.AwaitPersonTurnCompletedRequest(call_id="c7"))

        assert fake_restate_workflow_context.promised == ["person_turn_completed"]
        assert await_person_turn_completed_response.text == "Grace"
