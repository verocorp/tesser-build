from __future__ import annotations

import typing

import tesser.testing as ts
import restate

import calls.application.relays as relays
import calls.component as component
import calls.domain as domain
import pgdatabase.database as pgdatabase_database


@ts.fake
class FakeDurablePromise:  # tesser:debt TB072
    def __init__(self, resolved: bytes) -> None:
        self._resolved = resolved

    async def value(self) -> bytes:
        return self._resolved


@ts.fake
class FakeRestateWorkflowContext:  # tesser:debt TB072
    def __init__(self) -> None:
        self.called: list[tuple[str, str]] = []

    async def generic_call(self, service: str, handler: str, arg: bytes) -> bytes:
        self.called.append((service, handler))
        if handler == "record_call":
            return relays.RecordCallResponseSnapshot().serialize(
                relays.RecordCallResponse(
                    call_id=str(relays.RecordCallRequestSnapshot().deserialize(arg).call.identity)
                )
            )
        if handler == "dial_person":
            return relays.DialPersonResponseSnapshot().serialize(relays.DialPersonResponse(call_id="c7"))
        if handler == "hang_up":
            return relays.HangUpResponseSnapshot().serialize(relays.HangUpResponse(call_id="c7"))
        return relays.SayUtteranceResponseSnapshot().serialize(relays.SayUtteranceResponse(call_id="c7"))

    def promise(self, name: str, serde: object) -> FakeDurablePromise:
        if name == "person_turn_completed":
            return FakeDurablePromise(
                relays.AwaitPersonTurnCompletedResponseSnapshot().serialize(
                    relays.AwaitPersonTurnCompletedResponse(call_id="c7", text="Grace")
                )
            )
        return FakeDurablePromise(
            relays.AwaitPersonJoinedResponseSnapshot().serialize(relays.AwaitPersonJoinedResponse(call_id="c7"))
        )


@ts.helper
def _spec(
    storage: str = "postgres://a@b/c",
    ingress: str = "http://localhost:8080",
) -> component.Spec:
    return component.Spec(
        storage=storage,
        ingress=ingress,
        livekit_url="ws://livekit",
        livekit_api_key="key",
        livekit_api_secret="secret",
        livekit_agent_name="caller",
    )


class TestConfig:
    def test_a_postgres_coordinate_requests_that_database(self) -> None:
        config = component.Config(_spec(storage="postgres://a@b/c"))

        assert config.database == pgdatabase_database.DatabaseRequest("postgres://a@b/c")

    def test_a_config_carries_the_engine_ingress(self) -> None:
        config = component.Config(_spec(ingress="http://localhost:8080"))

        assert config.ingress == "http://localhost:8080"

    def test_a_config_carries_the_livekit_settings(self) -> None:
        config = component.Config(_spec())

        assert (
            config.livekit_url,
            config.livekit_api_key,
            config.livekit_api_secret,
            config.livekit_agent_name,
        ) == ("ws://livekit", "key", "secret", "caller")


class TestCalls:
    async def test_the_component_publishes_the_restate_runtime_it_wired(self) -> None:
        config = component.Config(_spec(storage="postgres://nobody@nowhere/none"))

        calls = component.Calls(config, pgdatabase_database.Database(config.database))
        registered = {
            registration.name: sorted(registration.handlers)
            for registration in (
                calls.restate_call_runtime.call_actions_service,
                calls.restate_call_runtime.dialing_actions_service,
                calls.restate_call_runtime.speech_actions_service,
                calls.restate_call_runtime.call_orchestrator_workflow,
            )
        }
        await calls.close()

        assert registered == {
            "CallActions": ["record_call"],
            "DialingActions": ["dial_person", "hang_up"],
            "SpeechActions": ["say_utterance"],
            "CallOrchestrator": ["conduct_call", "person_joined", "person_turn_completed"],
        }


class TestWorkflow:
    async def test_an_invocation_conducts_the_whole_call_through_the_services_named_for_each_relay(self) -> None:
        fake_restate_workflow_context = FakeRestateWorkflowContext()  # tesser:debt TB085

        async with component.Calls.Workflow().invocation(
            typing.cast(restate.WorkflowContext, fake_restate_workflow_context)
        ) as call_orchestrator:
            conduct_call_response = await call_orchestrator.conduct_call(
                relays.ConductCallRequest(call=domain.Call(domain.CallSpec(call_id="c7", person_name="")))
            )

        assert conduct_call_response.call_id == "c7"
        assert fake_restate_workflow_context.called == [
            ("DialingActions", "dial_person"),
            ("SpeechActions", "say_utterance"),
            ("SpeechActions", "say_utterance"),
            ("DialingActions", "hang_up"),
            ("CallActions", "record_call"),
        ]
