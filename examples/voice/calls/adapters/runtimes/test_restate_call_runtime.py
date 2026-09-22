from __future__ import annotations

import contextlib
import typing

import tesser.testing as ts
import restate

import calls.adapters.runtimes as runtimes
import calls.application.client as client
import calls.application.relays as relays
import calls.domain as domain


@ts.fake
class FakeCallApplicationClient(client.CallApplicationClient):
    def __init__(self) -> None:
        self.recorded: list[relays.RecordCallRequest] = []

    async def record_call(self, record_call_request: relays.RecordCallRequest) -> relays.RecordCallResponse:
        self.recorded.append(record_call_request)
        return relays.RecordCallResponse(call_id=str(record_call_request.call.identity))


@ts.fake
class FakeDialingApplicationClient(client.DialingApplicationClient):
    def __init__(self) -> None:
        self.dialed: list[relays.DialPersonRequest] = []
        self.hung_up: list[relays.HangUpRequest] = []

    async def dial_person(self, dial_person_request: relays.DialPersonRequest) -> relays.DialPersonResponse:
        self.dialed.append(dial_person_request)
        return relays.DialPersonResponse(call_id=str(dial_person_request.call.identity))

    async def hang_up(self, hang_up_request: relays.HangUpRequest) -> relays.HangUpResponse:
        self.hung_up.append(hang_up_request)
        return relays.HangUpResponse(call_id=str(hang_up_request.call.identity))


@ts.fake
class FakeSpeechApplicationClient(client.SpeechApplicationClient):
    def __init__(self) -> None:
        self.said: list[relays.SayUtteranceRequest] = []

    async def say_utterance(
        self, say_utterance_request: relays.SayUtteranceRequest
    ) -> relays.SayUtteranceResponse:
        self.said.append(say_utterance_request)
        return relays.SayUtteranceResponse(call_id=say_utterance_request.call_id)


@ts.fake
class FakeDurablePromise:  # tesser:debt TB072
    def __init__(self, resolved: list[tuple[str, object]], name: str) -> None:
        self._resolved = resolved
        self._name = name

    async def resolve(self, value: object) -> None:
        if any(name == self._name for name, _ in self._resolved):
            raise RuntimeError(f"promise {self._name!r} is already resolved")
        self._resolved.append((self._name, value))

    async def peek(self) -> object:
        for name, value in self._resolved:
            if name == self._name:
                return value
        return None



@ts.fake
class FakeCallOrchestratorApplicationClient(client.CallOrchestratorApplicationClient):
    def __init__(self) -> None:
        self.conducted: list[relays.ConductCallRequest] = []

    async def conduct_call(self, conduct_call_request: relays.ConductCallRequest) -> relays.ConductCallResponse:
        self.conducted.append(conduct_call_request)
        return relays.ConductCallResponse(call_id=str(conduct_call_request.call.identity))


@ts.fake
class FakeCallWorkflow:
    def __init__(self, fake_call_orchestrator_application_client: FakeCallOrchestratorApplicationClient) -> None:
        self._fake_call_orchestrator_application_client = fake_call_orchestrator_application_client
        self.opened: list[restate.WorkflowContext] = []

    @contextlib.asynccontextmanager
    async def invocation(
        self, restate_workflow_context: restate.WorkflowContext
    ) -> typing.AsyncIterator[FakeCallOrchestratorApplicationClient]:
        self.opened.append(restate_workflow_context)
        yield self._fake_call_orchestrator_application_client


@ts.fake
class FakeRestateWorkflowSharedContext:  # tesser:debt TB072
    def __init__(self) -> None:
        self.resolved: list[tuple[str, object]] = []

    def promise(self, name: str, serde: object) -> FakeDurablePromise:
        return FakeDurablePromise(self.resolved, name)


@ts.helper
def call_spec(call_id: str = "c7", person_name: str = "") -> domain.CallSpec:
    return domain.CallSpec(call_id=call_id, person_name=person_name)


class TestRestateCallRuntime:
    def test_it_registers_the_three_action_services_and_the_orchestrator_workflow(self) -> None:
        restate_call_runtime = runtimes.RestateCallRuntime(
            FakeCallApplicationClient(),
            FakeDialingApplicationClient(),
            FakeSpeechApplicationClient(),
            FakeCallWorkflow(FakeCallOrchestratorApplicationClient()),
        )

        registered = {
            registration.name: sorted(registration.handlers)
            for registration in (
                restate_call_runtime.call_actions_service,
                restate_call_runtime.dialing_actions_service,
                restate_call_runtime.speech_actions_service,
                restate_call_runtime.call_orchestrator_workflow,
            )
        }

        assert registered == {
            "CallActions": ["record_call"],
            "DialingActions": ["dial_person", "hang_up"],
            "SpeechActions": ["say_utterance"],
            "CallOrchestrator": ["conduct_call", "person_joined", "person_turn_completed"],
        }

    def test_every_registration_declares_a_bounded_retry_policy(self) -> None:
        restate_call_runtime = runtimes.RestateCallRuntime(
            FakeCallApplicationClient(),
            FakeDialingApplicationClient(),
            FakeSpeechApplicationClient(),
            FakeCallWorkflow(FakeCallOrchestratorApplicationClient()),
        )

        policies = [
            registration.invocation_retry_policy
            for registration in (
                restate_call_runtime.call_actions_service,
                restate_call_runtime.dialing_actions_service,
                restate_call_runtime.speech_actions_service,
                restate_call_runtime.call_orchestrator_workflow,
            )
        ]

        assert [(policy.max_attempts, policy.on_max_attempts) for policy in policies if policy is not None] == [
            (5, "pause")
        ] * 4

    async def test_the_record_call_handler_hands_the_request_to_the_application_client(self) -> None:
        fake_call_application_client = FakeCallApplicationClient()
        record_call_request = relays.RecordCallRequest(call=domain.Call(call_spec()))

        await runtimes.RestateCallRuntime(
            fake_call_application_client, FakeDialingApplicationClient(), FakeSpeechApplicationClient(), FakeCallWorkflow(FakeCallOrchestratorApplicationClient())
        ).record_call_handler(typing.cast(restate.Context, None), record_call_request)

        assert fake_call_application_client.recorded == [record_call_request]

    async def test_the_dial_person_handler_hands_the_request_to_the_application_client(self) -> None:
        fake_dialing_application_client = FakeDialingApplicationClient()
        dial_person_request = relays.DialPersonRequest(call=domain.Call(call_spec()))

        await runtimes.RestateCallRuntime(
            FakeCallApplicationClient(), fake_dialing_application_client, FakeSpeechApplicationClient(), FakeCallWorkflow(FakeCallOrchestratorApplicationClient())
        ).dial_person_handler(typing.cast(restate.Context, None), dial_person_request)

        assert fake_dialing_application_client.dialed == [dial_person_request]

    async def test_the_hang_up_handler_hands_the_request_to_the_application_client(self) -> None:
        fake_dialing_application_client = FakeDialingApplicationClient()
        hang_up_request = relays.HangUpRequest(call=domain.Call(call_spec()))

        await runtimes.RestateCallRuntime(
            FakeCallApplicationClient(), fake_dialing_application_client, FakeSpeechApplicationClient(), FakeCallWorkflow(FakeCallOrchestratorApplicationClient())
        ).hang_up_handler(typing.cast(restate.Context, None), hang_up_request)

        assert fake_dialing_application_client.hung_up == [hang_up_request]

    async def test_the_say_utterance_handler_hands_the_request_to_the_application_client(self) -> None:
        fake_speech_application_client = FakeSpeechApplicationClient()
        say_utterance_request = relays.SayUtteranceRequest(call_id="c7", text="Hello.")

        await runtimes.RestateCallRuntime(
            FakeCallApplicationClient(), FakeDialingApplicationClient(), fake_speech_application_client, FakeCallWorkflow(FakeCallOrchestratorApplicationClient())
        ).say_utterance_handler(typing.cast(restate.Context, None), say_utterance_request)

        assert fake_speech_application_client.said == [say_utterance_request]

    async def test_the_conduct_call_handler_opens_the_workflow_on_this_invocations_context(self) -> None:
        fake_call_workflow = FakeCallWorkflow(FakeCallOrchestratorApplicationClient())
        restate_workflow_context = typing.cast(restate.WorkflowContext, object())

        await runtimes.RestateCallRuntime(
            FakeCallApplicationClient(),
            FakeDialingApplicationClient(),
            FakeSpeechApplicationClient(),
            fake_call_workflow,
        ).conduct_call_handler(
            restate_workflow_context, relays.ConductCallRequest(call=domain.Call(call_spec(call_id="c7")))
        )

        assert fake_call_workflow.opened == [restate_workflow_context]

    async def test_the_conduct_call_handler_hands_the_request_to_the_orchestrator_the_workflow_built(self) -> None:
        fake_call_orchestrator_application_client = FakeCallOrchestratorApplicationClient()
        conduct_call_request = relays.ConductCallRequest(call=domain.Call(call_spec(call_id="c7")))

        restate_call_runtime = runtimes.RestateCallRuntime(
            FakeCallApplicationClient(),
            FakeDialingApplicationClient(),
            FakeSpeechApplicationClient(),
            FakeCallWorkflow(fake_call_orchestrator_application_client),
        )

        assert (
            await restate_call_runtime.conduct_call_handler(
                typing.cast(restate.WorkflowContext, object()), conduct_call_request
            )
        ).call_id == "c7"
        assert fake_call_orchestrator_application_client.conducted == [conduct_call_request]

    async def test_the_person_joined_handler_resolves_the_workflows_promise(self) -> None:
        restate_call_runtime = runtimes.RestateCallRuntime(
            FakeCallApplicationClient(),
            FakeDialingApplicationClient(),
            FakeSpeechApplicationClient(),
            FakeCallWorkflow(FakeCallOrchestratorApplicationClient()),
        )
        fake_restate_workflow_shared_context = FakeRestateWorkflowSharedContext()  # tesser:debt TB085

        await restate_call_runtime.person_joined_handler(
            typing.cast(restate.WorkflowSharedContext, fake_restate_workflow_shared_context),
            relays.PersonJoinedRequest(call_id="c7"),
        )

        assert fake_restate_workflow_shared_context.resolved == [
            (
                "person_joined",
                relays.AwaitPersonJoinedResponseSnapshot().serialize(relays.AwaitPersonJoinedResponse(call_id="c7")),
            )
        ]

    async def test_a_second_join_for_a_call_already_joined_is_acknowledged_not_failed(self) -> None:
        restate_call_runtime = runtimes.RestateCallRuntime(
            FakeCallApplicationClient(),
            FakeDialingApplicationClient(),
            FakeSpeechApplicationClient(),
            FakeCallWorkflow(FakeCallOrchestratorApplicationClient()),
        )
        fake_restate_workflow_shared_context = FakeRestateWorkflowSharedContext()  # tesser:debt TB085

        for _ in (1, 2):
            await restate_call_runtime.person_joined_handler(
                typing.cast(restate.WorkflowSharedContext, fake_restate_workflow_shared_context),
                relays.PersonJoinedRequest(call_id="c7"),
            )

        assert len(fake_restate_workflow_shared_context.resolved) == 1

    async def test_the_person_turn_completed_handler_resolves_the_promise_with_what_was_said(self) -> None:
        restate_call_runtime = runtimes.RestateCallRuntime(
            FakeCallApplicationClient(),
            FakeDialingApplicationClient(),
            FakeSpeechApplicationClient(),
            FakeCallWorkflow(FakeCallOrchestratorApplicationClient()),
        )
        fake_restate_workflow_shared_context = FakeRestateWorkflowSharedContext()  # tesser:debt TB085

        await restate_call_runtime.person_turn_completed_handler(
            typing.cast(restate.WorkflowSharedContext, fake_restate_workflow_shared_context),
            relays.PersonTurnCompletedRequest(call_id="c7", text="my name is Grace"),
        )

        assert fake_restate_workflow_shared_context.resolved == [
            (
                "person_turn_completed",
                relays.AwaitPersonTurnCompletedResponseSnapshot().serialize(
                    relays.AwaitPersonTurnCompletedResponse(call_id="c7", text="my name is Grace")
                ),
            )
        ]

    async def test_a_second_completed_turn_keeps_the_first_one_the_workflow_is_waiting_on(self) -> None:
        restate_call_runtime = runtimes.RestateCallRuntime(
            FakeCallApplicationClient(),
            FakeDialingApplicationClient(),
            FakeSpeechApplicationClient(),
            FakeCallWorkflow(FakeCallOrchestratorApplicationClient()),
        )
        fake_restate_workflow_shared_context = FakeRestateWorkflowSharedContext()  # tesser:debt TB085

        await restate_call_runtime.person_turn_completed_handler(
            typing.cast(restate.WorkflowSharedContext, fake_restate_workflow_shared_context),
            relays.PersonTurnCompletedRequest(call_id="c7", text="my name is Grace"),
        )
        await restate_call_runtime.person_turn_completed_handler(
            typing.cast(restate.WorkflowSharedContext, fake_restate_workflow_shared_context),
            relays.PersonTurnCompletedRequest(call_id="c7", text="Ada"),
        )

        assert fake_restate_workflow_shared_context.resolved == [
            (
                "person_turn_completed",
                relays.AwaitPersonTurnCompletedResponseSnapshot().serialize(
                    relays.AwaitPersonTurnCompletedResponse(call_id="c7", text="my name is Grace")
                ),
            )
        ]
