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


@ts.fake
class FakeDurablePromise:  # tesser:debt TB072

    def __init__(self, resolved: list[tuple[str, object]], name: str) -> None:
        self._resolved = resolved
        self._name = name

    async def resolve(self, value: object) -> None:
        self._resolved.append((self._name, value))


@ts.fake
class FakeRestateWorkflowSharedContext:  # tesser:debt TB072

    def __init__(self) -> None:
        self.resolved: list[tuple[str, object]] = []

    def promise(self, name: str, serde: object) -> FakeDurablePromise:
        return FakeDurablePromise(self.resolved, name)


@ts.fake
class FakeRestateObjectContext:  # tesser:debt TB072

    def __init__(self, key: str, state: dict[str, object]) -> None:
        self._key = key
        self.state = state
        self.resolved: list[tuple[str, object]] = []

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


class TestRestateCallRuntime:

    def test_it_registers_the_actions_service_the_orchestrator_workflow_and_the_utterance_mailbox(self) -> None:
        restate_call_runtime = runtimes.RestateCallRuntime(FakeCallsApplicationClient())

        registered = {
            restate_call_runtime.call_actions_service.name: sorted(restate_call_runtime.call_actions_service.handlers),
            restate_call_runtime.call_orchestrator_workflow.name: sorted(
                restate_call_runtime.call_orchestrator_workflow.handlers
            ),
            restate_call_runtime.call_utterances_object.name: sorted(
                restate_call_runtime.call_utterances_object.handlers
            ),
        }

        assert registered == {
            "CallActions": ["record_call"],
            "CallOrchestrator": ["conduct_call", "person_answered"],
            "CallUtterances": ["person_utterance", "take_person_utterance"],
        }

    def test_every_registration_declares_a_bounded_retry_policy(self) -> None:
        restate_call_runtime = runtimes.RestateCallRuntime(FakeCallsApplicationClient())

        policies = [
            restate_call_runtime.call_actions_service.invocation_retry_policy,
            restate_call_runtime.call_orchestrator_workflow.invocation_retry_policy,
            restate_call_runtime.call_utterances_object.invocation_retry_policy,
        ]

        assert [(policy.max_attempts, policy.on_max_attempts) for policy in policies if policy is not None] == [
            (5, "pause"),
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

    async def test_the_person_answered_handler_resolves_the_workflows_promise(self) -> None:
        restate_call_runtime = runtimes.RestateCallRuntime(FakeCallsApplicationClient())
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

        await runtimes.RestateCallRuntime(FakeCallsApplicationClient()).person_utterance_handler(
            typing.cast(restate.ObjectContext, fake_restate_object_context),
            relays.PersonUtteranceRequest(call_id="c7", text="Ada"),
        )

        assert fake_restate_object_context.state == {"buffered": ["my name is", "Ada"]}

    async def test_an_utterance_someone_is_waiting_for_resolves_their_awakeable(self) -> None:
        fake_restate_object_context = FakeRestateObjectContext("c7", {"waiting": "sign_1"})  # tesser:debt TB085

        await runtimes.RestateCallRuntime(FakeCallsApplicationClient()).person_utterance_handler(
            typing.cast(restate.ObjectContext, fake_restate_object_context),
            relays.PersonUtteranceRequest(call_id="c7", text="Ada"),
        )

        assert fake_restate_object_context.resolved == [
            ("sign_1", relays.AwaitPersonUtteranceResponse(call_id="c7", text="Ada"))
        ]
        assert fake_restate_object_context.state == {}

    async def test_taking_with_utterances_buffered_resolves_the_awakeable_with_the_oldest(self) -> None:
        fake_restate_object_context = FakeRestateObjectContext("c7", {"buffered": ["my name is", "Ada"]})  # tesser:debt TB085

        await runtimes.RestateCallRuntime(FakeCallsApplicationClient()).take_person_utterance_handler(
            typing.cast(restate.ObjectContext, fake_restate_object_context), "sign_1"
        )

        assert fake_restate_object_context.resolved == [
            ("sign_1", relays.AwaitPersonUtteranceResponse(call_id="c7", text="my name is"))
        ]
        assert fake_restate_object_context.state == {"buffered": ["Ada"]}

    async def test_taking_with_nothing_buffered_leaves_the_awakeable_waiting(self) -> None:
        fake_restate_object_context = FakeRestateObjectContext("c7", {})  # tesser:debt TB085

        await runtimes.RestateCallRuntime(FakeCallsApplicationClient()).take_person_utterance_handler(
            typing.cast(restate.ObjectContext, fake_restate_object_context), "sign_1"
        )

        assert fake_restate_object_context.state == {"waiting": "sign_1"}
        assert fake_restate_object_context.resolved == []
