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
        self.spoken: list[relays.SpeakTurnRequest] = []

    async def speak_turn(self, speak_turn_request: relays.SpeakTurnRequest) -> relays.SpeakTurnResponse:
        self.spoken.append(speak_turn_request)
        if len(self.spoken) == 2:
            return relays.SpeakTurnResponse(
                call_id=str(speak_turn_request.call.identity), text="nice to meet you, Grace", person_names=("Grace",)
            )
        return relays.SpeakTurnResponse(
            call_id=str(speak_turn_request.call.identity), text="hi, may I have your name?", person_names=()
        )


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
        assert isinstance(arg, relays.SpeakTurnRequest)
        return await self._fake_speech_application_client.speak_turn(arg)

    def promise(self, name: str, serde: object) -> FakeDurablePromise:
        return FakeDurablePromise(self.resolved, name, relays.AwaitPersonAnsweredResponse(call_id="c7"))

    def awakeable(self, serde: object) -> tuple[str, FakeDurableFuture]:
        return "sign_1", FakeDurableFuture(relays.AwaitPersonUtteranceResponse(call_id="c7", text="my name is Grace"))

    def object_send(self, tpe: object, key: str, arg: object) -> None:
        return None


@ts.fake
class FakeRestateWorkflowSharedContext:  # tesser:debt TB072

    def __init__(self) -> None:
        self.resolved: list[tuple[str, object]] = []

    def promise(self, name: str, serde: object) -> FakeDurablePromise:
        return FakeDurablePromise(self.resolved, name, None)


@ts.fake
class FakeRestateObjectContext:  # tesser:debt TB072

    def __init__(self, key: str, state: dict[str, object]) -> None:
        self._key = key
        self.state = state
        self.resolved: list[tuple[str, object]] = []
        self.rejected: list[str] = []

    def key(self) -> str:
        return self._key

    async def get(self, name: str, type_hint: object) -> object:
        return self.state.get(name)

    def set(self, name: str, value: object) -> None:
        self.state[name] = value

    def clear(self, name: str) -> None:
        self.state.pop(name, None)

    def resolve_awakeable(self, name: str, value: object, serde: object) -> None:
        self.resolved.append((name, value))

    def reject_awakeable(self, name: str, failure_message: str) -> None:
        self.rejected.append(name)


@ts.helper
def call_spec(call_id: str = "c7", name: str = "Ada", phone_number: str = "+15555550100") -> domain.CallSpec:
    return domain.CallSpec(
        call_id=call_id, person=domain.PersonSpec(name=name, phone_number=phone_number), turns=(), step="ask_name"
    )


class TestRestateCallRuntime:

    def test_it_registers_the_actions_services_the_orchestrator_workflow_and_the_utterance_mailbox(self) -> None:
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
                restate_call_runtime.call_utterances_object,
            )
        }

        assert registered == {
            "CallActions": ["record_call"],
            "DialingActions": ["dial_person", "hang_up"],
            "SpeechActions": ["speak_turn"],
            "CallOrchestrator": ["conduct_call", "person_answered"],
            "CallUtterances": ["person_utterance", "take_person_utterance"],
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
                restate_call_runtime.call_utterances_object,
            )
        ]

        assert [(policy.max_attempts, policy.on_max_attempts) for policy in policies if policy is not None] == [
            (5, "pause")
        ] * 5

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

    async def test_the_speak_turn_handler_hands_the_request_to_the_application_client(self) -> None:
        fake_speech_application_client = FakeSpeechApplicationClient()
        speak_turn_request = relays.SpeakTurnRequest(call=domain.Call(call_spec()))

        await runtimes.RestateCallRuntime(
            FakeCallApplicationClient(), FakeDialingApplicationClient(), fake_speech_application_client
        ).speak_turn_handler(typing.cast(restate.Context, None), speak_turn_request)

        assert fake_speech_application_client.spoken == [speak_turn_request]

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
        assert [str(recorded.call.person.name) for recorded in fake_call_application_client.recorded] == ["Grace"]
        assert len(fake_dialing_application_client.dialed) == 1
        assert len(fake_dialing_application_client.hung_up) == 1

    async def test_the_person_answered_handler_resolves_the_workflows_promise(self) -> None:
        restate_call_runtime = runtimes.RestateCallRuntime(
            FakeCallApplicationClient(), FakeDialingApplicationClient(), FakeSpeechApplicationClient()
        )
        fake_restate_workflow_shared_context = FakeRestateWorkflowSharedContext()  # tesser:debt TB085

        await restate_call_runtime.person_answered_handler(
            typing.cast(restate.WorkflowSharedContext, fake_restate_workflow_shared_context),
            relays.PersonAnsweredRequest(call_id="c7"),
        )

        assert fake_restate_workflow_shared_context.resolved == [
            (restate_call_runtime.person_answered_promise, relays.AwaitPersonAnsweredResponse(call_id="c7"))
        ]

    async def test_an_utterance_nobody_is_waiting_for_is_buffered_in_order(self) -> None:
        fake_restate_object_context = FakeRestateObjectContext("c7", {"buffered": ["my name is"]})  # tesser:debt TB085

        await runtimes.RestateCallRuntime(
            FakeCallApplicationClient(), FakeDialingApplicationClient(), FakeSpeechApplicationClient()
        ).person_utterance_handler(
            typing.cast(restate.ObjectContext, fake_restate_object_context),
            relays.PersonUtteranceRequest(call_id="c7", text="Ada"),
        )

        assert fake_restate_object_context.state == {"buffered": ["my name is", "Ada"]}

    async def test_an_utterance_someone_is_waiting_for_resolves_their_awakeable(self) -> None:
        fake_restate_object_context = FakeRestateObjectContext("c7", {"waiting": "sign_1"})  # tesser:debt TB085

        await runtimes.RestateCallRuntime(
            FakeCallApplicationClient(), FakeDialingApplicationClient(), FakeSpeechApplicationClient()
        ).person_utterance_handler(
            typing.cast(restate.ObjectContext, fake_restate_object_context),
            relays.PersonUtteranceRequest(call_id="c7", text="Ada"),
        )

        assert fake_restate_object_context.resolved == [
            ("sign_1", relays.AwaitPersonUtteranceResponse(call_id="c7", text="Ada"))
        ]
        assert fake_restate_object_context.state == {}

    async def test_taking_with_utterances_buffered_resolves_the_awakeable_with_the_oldest(self) -> None:
        fake_restate_object_context = FakeRestateObjectContext("c7", {"buffered": ["my name is", "Ada"]})  # tesser:debt TB085

        await runtimes.RestateCallRuntime(
            FakeCallApplicationClient(), FakeDialingApplicationClient(), FakeSpeechApplicationClient()
        ).take_person_utterance_handler(typing.cast(restate.ObjectContext, fake_restate_object_context), "sign_1")

        assert fake_restate_object_context.resolved == [
            ("sign_1", relays.AwaitPersonUtteranceResponse(call_id="c7", text="my name is"))
        ]
        assert fake_restate_object_context.state == {"buffered": ["Ada"]}

    async def test_taking_with_nothing_buffered_leaves_the_awakeable_waiting(self) -> None:
        fake_restate_object_context = FakeRestateObjectContext("c7", {})  # tesser:debt TB085

        await runtimes.RestateCallRuntime(
            FakeCallApplicationClient(), FakeDialingApplicationClient(), FakeSpeechApplicationClient()
        ).take_person_utterance_handler(typing.cast(restate.ObjectContext, fake_restate_object_context), "sign_1")

        assert fake_restate_object_context.state == {"waiting": "sign_1"}
        assert fake_restate_object_context.resolved == []

    async def test_a_second_answer_for_a_call_already_answered_is_acknowledged_not_failed(self) -> None:
        restate_call_runtime = runtimes.RestateCallRuntime(
            FakeCallApplicationClient(), FakeDialingApplicationClient(), FakeSpeechApplicationClient()
        )
        fake_restate_workflow_shared_context = FakeRestateWorkflowSharedContext()  # tesser:debt TB085

        for _ in (1, 2):
            await restate_call_runtime.person_answered_handler(
                typing.cast(restate.WorkflowSharedContext, fake_restate_workflow_shared_context),
                relays.PersonAnsweredRequest(call_id="c7"),
            )

        assert len(fake_restate_workflow_shared_context.resolved) == 1

    async def test_a_second_taker_does_not_displace_the_one_already_waiting(self) -> None:
        fake_restate_object_context = FakeRestateObjectContext("c7", {"waiting": "sign_1"})  # tesser:debt TB085

        await runtimes.RestateCallRuntime(
            FakeCallApplicationClient(), FakeDialingApplicationClient(), FakeSpeechApplicationClient()
        ).take_person_utterance_handler(typing.cast(restate.ObjectContext, fake_restate_object_context), "sign_2")

        assert fake_restate_object_context.state["waiting"] == "sign_1"
        assert fake_restate_object_context.rejected == ["sign_2"]
