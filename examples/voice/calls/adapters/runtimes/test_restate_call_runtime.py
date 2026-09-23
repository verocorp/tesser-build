from __future__ import annotations

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
class FakeDurableFuture:  # tesser:debt TB072
    def __init__(self, resolved: object) -> None:
        self._resolved = resolved

    def __await__(self) -> typing.Generator[None, None, object]:
        yield
        return self._resolved


@ts.fake
class FakeDurablePromise:  # tesser:debt TB072
    def __init__(self, resolved: list[tuple[str, object]], name: str, value: object) -> None:
        self._resolved = resolved
        self._name = name
        self._value = value

    async def resolve(self, value: object) -> None:
        if any(name == self._name for name, _ in self._resolved):
            raise RuntimeError(f"promise {self._name!r} is already resolved")
        self._resolved.append((self._name, value))

    async def peek(self) -> object:
        for name, value in self._resolved:
            if name == self._name:
                return value
        return None

    def value(self) -> FakeDurableFuture:
        return FakeDurableFuture(self._value)


@ts.fake
class FakeRestateWorkflowContext:  # tesser:debt TB072
    def __init__(
        self,
        fake_call_application_client: FakeCallApplicationClient,
        fake_dialing_application_client: FakeDialingApplicationClient,
        fake_speech_application_client: FakeSpeechApplicationClient,
    ) -> None:
        self._fake_call_application_client = fake_call_application_client
        self._fake_dialing_application_client = fake_dialing_application_client
        self._fake_speech_application_client = fake_speech_application_client
        self.resolved: list[tuple[str, object]] = []

    async def service_call(self, tpe: object, arg: object) -> object:
        if isinstance(arg, relays.RecordCallRequest):
            return await self._fake_call_application_client.record_call(arg)
        if isinstance(arg, relays.DialPersonRequest):
            return await self._fake_dialing_application_client.dial_person(arg)
        if isinstance(arg, relays.HangUpRequest):
            return await self._fake_dialing_application_client.hang_up(arg)
        assert isinstance(arg, relays.SayUtteranceRequest)
        return await self._fake_speech_application_client.say_utterance(arg)

    def promise(self, name: str, serde: object) -> FakeDurablePromise:
        if name == "person_turn_completed":
            return FakeDurablePromise(
                self.resolved, name, relays.AwaitPersonTurnCompletedResponse(call_id="c7", text="Grace")
            )
        return FakeDurablePromise(self.resolved, name, relays.AwaitPersonJoinedResponse(call_id="c7"))


@ts.fake
class FakeRestateWorkflowSharedContext:  # tesser:debt TB072
    def __init__(self) -> None:
        self.resolved: list[tuple[str, object]] = []

    def promise(self, name: str, serde: object) -> FakeDurablePromise:
        return FakeDurablePromise(self.resolved, name, None)


@ts.helper
def call_spec(call_id: str = "c7", person_name: str = "") -> domain.CallSpec:
    return domain.CallSpec(call_id=call_id, person_name=person_name)


class TestRestateCallRuntime:
    def test_it_registers_the_three_action_services_and_the_orchestrator_workflow(self) -> None:
        restate_call_runtime = runtimes.RestateCallRuntime(
            FakeCallApplicationClient(), FakeDialingApplicationClient(), FakeSpeechApplicationClient()
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
            FakeCallApplicationClient(), FakeDialingApplicationClient(), FakeSpeechApplicationClient()
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
            fake_call_application_client, FakeDialingApplicationClient(), FakeSpeechApplicationClient()
        ).record_call_handler(typing.cast(restate.Context, None), record_call_request)

        assert fake_call_application_client.recorded == [record_call_request]

    async def test_the_dial_person_handler_hands_the_request_to_the_application_client(self) -> None:
        fake_dialing_application_client = FakeDialingApplicationClient()
        dial_person_request = relays.DialPersonRequest(call=domain.Call(call_spec()))

        await runtimes.RestateCallRuntime(
            FakeCallApplicationClient(), fake_dialing_application_client, FakeSpeechApplicationClient()
        ).dial_person_handler(typing.cast(restate.Context, None), dial_person_request)

        assert fake_dialing_application_client.dialed == [dial_person_request]

    async def test_the_hang_up_handler_hands_the_request_to_the_application_client(self) -> None:
        fake_dialing_application_client = FakeDialingApplicationClient()
        hang_up_request = relays.HangUpRequest(call=domain.Call(call_spec()))

        await runtimes.RestateCallRuntime(
            FakeCallApplicationClient(), fake_dialing_application_client, FakeSpeechApplicationClient()
        ).hang_up_handler(typing.cast(restate.Context, None), hang_up_request)

        assert fake_dialing_application_client.hung_up == [hang_up_request]

    async def test_the_say_utterance_handler_hands_the_request_to_the_application_client(self) -> None:
        fake_speech_application_client = FakeSpeechApplicationClient()
        say_utterance_request = relays.SayUtteranceRequest(call_id="c7", text="Hello.")

        await runtimes.RestateCallRuntime(
            FakeCallApplicationClient(), FakeDialingApplicationClient(), fake_speech_application_client
        ).say_utterance_handler(typing.cast(restate.Context, None), say_utterance_request)

        assert fake_speech_application_client.said == [say_utterance_request]

    async def test_the_conduct_call_handler_runs_the_whole_call_inside_this_invocation(self) -> None:
        fake_call_application_client = FakeCallApplicationClient()
        fake_dialing_application_client = FakeDialingApplicationClient()
        fake_speech_application_client = FakeSpeechApplicationClient()
        fake_restate_workflow_context = FakeRestateWorkflowContext(  # tesser:debt TB085
            fake_call_application_client, fake_dialing_application_client, fake_speech_application_client
        )

        conduct_call_response = await runtimes.RestateCallRuntime(  # tesser:debt TB085
            fake_call_application_client, fake_dialing_application_client, fake_speech_application_client
        ).conduct_call_handler(
            typing.cast(restate.WorkflowContext, fake_restate_workflow_context),
            relays.ConductCallRequest(call=domain.Call(call_spec(call_id="c7"))),
        )

        assert conduct_call_response.call_id == "c7"
        assert [str(recorded.call.person_name) for recorded in fake_call_application_client.recorded] == ["Grace"]

    async def test_the_person_joined_handler_resolves_the_workflows_promise(self) -> None:
        restate_call_runtime = runtimes.RestateCallRuntime(
            FakeCallApplicationClient(), FakeDialingApplicationClient(), FakeSpeechApplicationClient()
        )
        fake_restate_workflow_shared_context = FakeRestateWorkflowSharedContext()  # tesser:debt TB085

        await restate_call_runtime.person_joined_handler(
            typing.cast(restate.WorkflowSharedContext, fake_restate_workflow_shared_context),
            relays.PersonJoinedRequest(call_id="c7"),
        )

        assert fake_restate_workflow_shared_context.resolved == [
            (restate_call_runtime.person_joined_promise, relays.AwaitPersonJoinedResponse(call_id="c7"))
        ]

    async def test_a_second_join_for_a_call_already_joined_is_acknowledged_not_failed(self) -> None:
        restate_call_runtime = runtimes.RestateCallRuntime(
            FakeCallApplicationClient(), FakeDialingApplicationClient(), FakeSpeechApplicationClient()
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
            FakeCallApplicationClient(), FakeDialingApplicationClient(), FakeSpeechApplicationClient()
        )
        fake_restate_workflow_shared_context = FakeRestateWorkflowSharedContext()  # tesser:debt TB085

        await restate_call_runtime.person_turn_completed_handler(
            typing.cast(restate.WorkflowSharedContext, fake_restate_workflow_shared_context),
            relays.PersonTurnCompletedRequest(call_id="c7", text="my name is Grace"),
        )

        assert fake_restate_workflow_shared_context.resolved == [
            (
                restate_call_runtime.person_turn_completed_promise,
                relays.AwaitPersonTurnCompletedResponse(call_id="c7", text="my name is Grace"),
            )
        ]

    async def test_a_second_completed_turn_keeps_the_first_one_the_workflow_is_waiting_on(self) -> None:
        restate_call_runtime = runtimes.RestateCallRuntime(
            FakeCallApplicationClient(), FakeDialingApplicationClient(), FakeSpeechApplicationClient()
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
                restate_call_runtime.person_turn_completed_promise,
                relays.AwaitPersonTurnCompletedResponse(call_id="c7", text="my name is Grace"),
            )
        ]
