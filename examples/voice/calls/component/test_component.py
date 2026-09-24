from __future__ import annotations

import tesser.testing as ts

import calls.component as component
import pgdatabase.database as pgdatabase_database


@ts.helper
def _spec(
    storage: str = "postgres://a@b/c",
    restate_url: str = "http://localhost:8080",
) -> component.Spec:
    return component.Spec(
        storage=storage,
        restate_url=restate_url,
        livekit_url="ws://livekit",
        livekit_api_key="key",
        livekit_api_secret="secret",
        livekit_agent_name="caller",
    )


class TestConfig:
    def test_a_postgres_coordinate_requests_that_database(self) -> None:
        config = component.Config(_spec(storage="postgres://a@b/c"))

        assert config.database == pgdatabase_database.DatabaseRequest("postgres://a@b/c")

    def test_a_config_carries_the_restate_url(self) -> None:
        config = component.Config(_spec(restate_url="http://localhost:8080"))

        assert config.restate_url == "http://localhost:8080"

    def test_a_config_carries_the_livekit_settings(self) -> None:
        config = component.Config(_spec())

        assert (
            config.livekit_url,
            config.livekit_api_key,
            config.livekit_api_secret,
            config.livekit_agent_name,
        ) == ("ws://livekit", "key", "secret", "caller")


class TestCalls:
    async def test_the_component_publishes_the_restate_services_and_workflow_it_registered_into(self) -> None:
        config = component.Config(_spec(storage="postgres://nobody@nowhere/none"))

        calls = component.Calls(config, pgdatabase_database.Database(config.database))
        registered = {
            registration.name: sorted(registration.handlers)
            for registration in (
                calls.call_actions_service,
                calls.dialing_actions_service,
                calls.speech_actions_service,
                calls.call_orchestrator_workflow,
            )
        }
        await calls.close()

        assert registered == {
            "CallActions": ["record_call"],
            "DialingActions": ["dial_person", "hang_up"],
            "SpeechActions": ["say_utterance"],
            "CallOrchestrator": ["conduct_call", "person_joined", "person_turn_completed"],
        }

    async def test_every_registration_declares_a_bounded_retry_policy(self) -> None:
        config = component.Config(_spec(storage="postgres://nobody@nowhere/none"))

        calls = component.Calls(config, pgdatabase_database.Database(config.database))
        policies = [
            registration.invocation_retry_policy
            for registration in (
                calls.call_actions_service,
                calls.dialing_actions_service,
                calls.speech_actions_service,
                calls.call_orchestrator_workflow,
            )
        ]
        await calls.close()

        assert [(policy.max_attempts, policy.on_max_attempts) for policy in policies if policy is not None] == [
            (5, "pause")
        ] * 4

    async def test_only_the_workflow_is_reachable_from_ingress(self) -> None:
        config = component.Config(_spec(storage="postgres://nobody@nowhere/none"))

        calls = component.Calls(config, pgdatabase_database.Database(config.database))
        private = [
            registration.ingress_private
            for registration in (
                calls.call_actions_service,
                calls.dialing_actions_service,
                calls.speech_actions_service,
                calls.call_orchestrator_workflow,
            )
        ]
        await calls.close()

        assert private == [True, True, True, None]
