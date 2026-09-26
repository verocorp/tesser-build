from __future__ import annotations

import typing

import tesser.component as ts
import restate

import calls.adapters.activities as activities
import calls.adapters.dispatchers as dispatchers
import calls.adapters.gateways as gateways
import calls.adapters.repositories as repositories
import calls.adapters.workflows as workflows
import calls.application as application
import calls.client as client
import pgdatabase.database as pgdatabase_database

_RETRY_POLICY: typing.Final[restate.InvocationRetryPolicy] = restate.InvocationRetryPolicy(
    max_attempts=5, on_max_attempts="pause"
)


class Spec(ts.Spec):
    def __init__(
        self,
        storage: str,
        restate_url: str,
        livekit_url: str,
        livekit_api_key: str,
        livekit_api_secret: str,
        livekit_agent_name: str,
    ) -> None:
        self.storage = storage
        self.restate_url = restate_url
        self.livekit_url = livekit_url
        self.livekit_api_key = livekit_api_key
        self.livekit_api_secret = livekit_api_secret
        self.livekit_agent_name = livekit_agent_name


class Config(ts.Config):
    def __init__(self, spec: Spec) -> None:
        self.storage = spec.storage
        self.restate_url = spec.restate_url
        self.livekit_url = spec.livekit_url
        self.livekit_api_key = spec.livekit_api_key
        self.livekit_api_secret = spec.livekit_api_secret
        self.livekit_agent_name = spec.livekit_agent_name
        self.database = pgdatabase_database.DatabaseRequest(spec.storage)


class Calls(ts.Component):
    class Client:
        def __init__(
            self,
            call_service: application.CallService,
            call_events_service: application.CallEventsService,
            agent_service: application.AgentService,
        ) -> None:
            self._call_service = call_service
            self._call_events_service = call_events_service
            self._agent_service = agent_service

        async def place_call(self, place_call_request: client.PlaceCallRequest) -> client.PlaceCallResponse:
            return await self._call_service.place_call(place_call_request)

        async def get_call(self, get_call_request: client.GetCallRequest) -> client.GetCallResponse:
            return await self._call_service.get_call(get_call_request)

        async def person_joined(
            self, person_joined_request: client.PersonJoinedRequest
        ) -> client.PersonJoinedResponse:
            return await self._call_events_service.person_joined(person_joined_request)

        async def person_turn_completed(
            self, person_turn_completed_request: client.PersonTurnCompletedRequest
        ) -> client.PersonTurnCompletedResponse:
            return await self._call_events_service.person_turn_completed(person_turn_completed_request)

        async def attend_call(self, attend_call_request: client.AttendCallRequest) -> client.AttendCallResponse:
            return await self._agent_service.attend_call(attend_call_request)

        async def speak_utterance(
            self, speak_utterance_request: client.SpeakUtteranceRequest
        ) -> client.SpeakUtteranceResponse:
            return await self._agent_service.speak_utterance(speak_utterance_request)

    def __init__(self, config: Config, database: pgdatabase_database.Database) -> None:
        self._postgres_call_store = repositories.PostgresCallStore(database)
        self.call_actions_service: restate.Service = restate.Service(
            "CallActions", ingress_private=True, invocation_retry_policy=_RETRY_POLICY
        )
        self.dialing_actions_service: restate.Service = restate.Service(
            "DialingActions", ingress_private=True, invocation_retry_policy=_RETRY_POLICY
        )
        self.speech_actions_service: restate.Service = restate.Service(
            "SpeechActions", ingress_private=True, invocation_retry_policy=_RETRY_POLICY
        )
        self.call_orchestrator_workflow: restate.Workflow = restate.Workflow(
            "CallOrchestrator", invocation_retry_policy=_RETRY_POLICY
        )
        dialing_actions = application.DialingActions(
            gateways.LivekitDialing(
                config.livekit_url,
                config.livekit_api_key,
                config.livekit_api_secret,
                config.livekit_agent_name,
            )
        )
        restate_record_call = activities.RestateRecordCall(
            self.call_actions_service, application.CallActions(self._postgres_call_store)
        )
        restate_dial_person = activities.RestateDialPerson(self.dialing_actions_service, dialing_actions)
        restate_hang_up = activities.RestateHangUp(self.dialing_actions_service, dialing_actions)
        restate_say_utterance = activities.RestateSayUtterance(
            self.speech_actions_service,
            application.SpeechActions(
                gateways.LivekitSpeech(
                    gateways.LivekitAgentRpc(
                        config.livekit_url,
                        config.livekit_api_key,
                        config.livekit_api_secret,
                        config.livekit_agent_name,
                    )
                )
            ),
        )
        restate_conduct_call = workflows.RestateConductCall(
            self.call_orchestrator_workflow,
            restate_record_call,
            restate_dial_person,
            restate_hang_up,
            restate_say_utterance,
        )
        restate_person_joined = dispatchers.RestatePersonJoined(self.call_orchestrator_workflow)
        restate_person_turn_completed = dispatchers.RestatePersonTurnCompleted(self.call_orchestrator_workflow)
        restate_http_call_orchestrator_relay = dispatchers.RestateHttpCallOrchestratorRelay(
            config.restate_url,
            restate_conduct_call,
            restate_person_joined,
            restate_person_turn_completed,
        )
        self.client: client.CallsClient = Calls.Client(
            application.CallService(restate_http_call_orchestrator_relay, self._postgres_call_store),
            application.CallEventsService(restate_http_call_orchestrator_relay),
            application.AgentService(),
        )

    async def close(self) -> None:
        return None
