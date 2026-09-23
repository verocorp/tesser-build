from __future__ import annotations

import contextlib
import typing

import tesser.testing as ts

import calls.application as application
import calls.application.ports as ports
import calls.application.relays as relays
import calls.client as client
import calls.component as component
import pgdatabase.database as pgdatabase_database


@ts.fake
class FakeCallOrchestratorRelay(relays.CallOrchestratorRelay):

    def __init__(self) -> None:
        self.conducted: list[relays.ConductCallRequest] = []
        self.joined: list[relays.PersonJoinedRequest] = []
        self.completed: list[relays.PersonTurnCompletedRequest] = []

    async def run_conduct_call(self, conduct_call_request: relays.ConductCallRequest) -> relays.ConductCallResponse:
        self.conducted.append(conduct_call_request)
        return relays.ConductCallResponse(call_id=str(conduct_call_request.call.identity))

    async def run_person_joined(
        self, person_joined_request: relays.PersonJoinedRequest
    ) -> relays.PersonJoinedResponse:
        self.joined.append(person_joined_request)
        return relays.PersonJoinedResponse(call_id=person_joined_request.call_id)

    async def run_person_turn_completed(
        self, person_turn_completed_request: relays.PersonTurnCompletedRequest
    ) -> relays.PersonTurnCompletedResponse:
        self.completed.append(person_turn_completed_request)
        return relays.PersonTurnCompletedResponse(call_id=person_turn_completed_request.call_id)


@ts.fake
class FakeCallRepository(ports.CallRepository):

    def __init__(self, calls: dict[str, ports.Call]) -> None:
        self._calls = calls

    async def issue_call_id(self, issue_call_id_request: ports.IssueCallIdRequest) -> ports.IssueCallIdResponse:
        return ports.IssueCallIdResponse(call_id="issued-1")

    async def save_call(self, save_call_request: ports.SaveCallRequest) -> ports.SaveCallResponse:
        self._calls[save_call_request.call_id] = ports.Call(
            call_id=save_call_request.call_id, person_name=save_call_request.person_name
        )
        return ports.SaveCallResponse(call_id=save_call_request.call_id)

    async def load_call(self, load_call_request: ports.LoadCallRequest) -> ports.LoadCallResponse:
        if load_call_request.call_id not in self._calls:
            return ports.LoadCallResponse(outcome=ports.LoadCallOutcome.NOT_FOUND, calls=())
        return ports.LoadCallResponse(
            outcome=ports.LoadCallOutcome.FOUND, calls=(self._calls[load_call_request.call_id],)
        )


@ts.fake
class FakeCallStore(ports.CallStore):

    def __init__(self) -> None:
        self.calls: dict[str, ports.Call] = {}

    @contextlib.asynccontextmanager
    async def transaction(self) -> typing.AsyncIterator[ports.CallRepository]:
        yield FakeCallRepository(self.calls)


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


class TestClient:
    async def test_each_use_case_reaches_the_service_that_owns_it(self) -> None:
        fake_call_orchestrator_relay = FakeCallOrchestratorRelay()
        fake_call_store = FakeCallStore()
        fake_call_store.calls["c1"] = ports.Call(call_id="c1", person_name="Grace")
        calls_client: client.CallsClient = component.Calls.Client(
            application.CallService(fake_call_orchestrator_relay, fake_call_store),
            application.CallEventsService(fake_call_orchestrator_relay),
            application.AgentService(),
        )

        place_call_response = await calls_client.place_call(client.PlaceCallRequest())
        get_call_response = await calls_client.get_call(client.GetCallRequest(call_id="c1"))
        person_joined_response = await calls_client.person_joined(client.PersonJoinedRequest(call_id="p1"))
        person_turn_completed_response = await calls_client.person_turn_completed(
            client.PersonTurnCompletedRequest(call_id="t1", text="my name is Grace")
        )
        attend_call_response = await calls_client.attend_call(client.AttendCallRequest(call_id="a1"))
        speak_utterance_response = await calls_client.speak_utterance(
            client.SpeakUtteranceRequest(call_id="s1", text="Hello.")
        )

        assert [str(conducted.call.identity) for conducted in fake_call_orchestrator_relay.conducted] == [
            place_call_response.call_id
        ]
        assert get_call_response.call.person_name == "Grace"
        assert [joined.call_id for joined in fake_call_orchestrator_relay.joined] == ["p1"]
        assert person_joined_response.call_id == "p1"
        assert [completed.call_id for completed in fake_call_orchestrator_relay.completed] == ["t1"]
        assert person_turn_completed_response.call_id == "t1"
        assert attend_call_response.call_id == "a1"
        assert (speak_utterance_response.call_id, speak_utterance_response.text) == ("s1", "Hello.")


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
