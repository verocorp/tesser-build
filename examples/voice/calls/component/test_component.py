from __future__ import annotations

import tesser.testing as ts

import calls.component as component
import pgdatabase.database as pgdatabase_database


@ts.helper
def spec(storage: str = "postgres://a@b/c", ingress: str = "http://localhost:8080") -> component.Spec:
    return component.Spec(
        storage=storage,
        ingress=ingress,
        livekit_url="ws://livekit",
        livekit_api_key="key",
        livekit_api_secret="secret",
        livekit_agent_name="caller",
        livekit_sip_trunk_id="ST_1",
    )


class TestConfig:

    def test_a_postgres_coordinate_requests_that_database(self) -> None:
        config = component.Config(spec(storage="postgres://a@b/c"))

        assert config.database == pgdatabase_database.DatabaseRequest("postgres://a@b/c")

    def test_a_config_carries_the_engine_ingress(self) -> None:
        config = component.Config(spec(ingress="http://localhost:8080"))

        assert config.ingress == "http://localhost:8080"

    def test_a_config_carries_the_livekit_settings(self) -> None:
        config = component.Config(spec())

        assert (
            config.livekit_url,
            config.livekit_api_key,
            config.livekit_api_secret,
            config.livekit_agent_name,
            config.livekit_sip_trunk_id,
        ) == ("ws://livekit", "key", "secret", "caller", "ST_1")


class TestCalls:

    async def test_the_component_publishes_the_restate_runtime_it_wired(self) -> None:
        config = component.Config(spec(storage="postgres://nobody@nowhere/none"))

        calls = component.Calls(config, pgdatabase_database.Database(config.database))
        registered = {
            registration.name: sorted(registration.handlers)
            for registration in (
                calls.restate_call_runtime.call_actions_service,
                calls.restate_call_runtime.dialing_actions_service,
                calls.restate_call_runtime.speech_actions_service,
                calls.restate_call_runtime.call_orchestrator_workflow,
                calls.restate_call_runtime.call_utterances_object,
            )
        }
        await calls.close()

        assert registered == {
            "CallActions": ["record_call"],
            "DialingActions": ["dial_person", "hang_up"],
            "SpeechActions": ["end_person_turn", "speak_turn"],
            "CallOrchestrator": ["conduct_call", "person_answered"],
            "CallUtterances": ["person_utterance", "stop_taking_person_utterance", "take_person_utterance"],
        }
