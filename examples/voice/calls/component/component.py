from __future__ import annotations

import typing

import tesser.component as ts
import httpx
import livekit.api as livekit_api
import livekit.rtc as livekit_rtc
import restate
import restate.client as restate_client

import calls.adapters.a as a
import calls.adapters.b as b
import calls.adapters.c as c
import calls.adapters.gateways as gateways
import calls.adapters.repositories as repositories
import calls.application as application
import calls.client as client
import pgdatabase.database as pgdatabase_database

_RETRY_POLICY: typing.Final[restate.InvocationRetryPolicy] = restate.InvocationRetryPolicy(
    max_attempts=5, on_max_attempts="pause"
)
_INGRESS_TIMEOUT: typing.Final[httpx.Timeout] = httpx.Timeout(5.0, read=None)


class Spec(ts.Spec):
    def __init__(
        self,
        storage: str,
        ingress: str,
        livekit_url: str,
        livekit_api_key: str,
        livekit_api_secret: str,
        livekit_agent_name: str,
    ) -> None:
        self.storage = storage
        self.ingress = ingress
        self.livekit_url = livekit_url
        self.livekit_api_key = livekit_api_key
        self.livekit_api_secret = livekit_api_secret
        self.livekit_agent_name = livekit_agent_name


class Config(ts.Config):
    def __init__(self, spec: Spec) -> None:
        self.storage = spec.storage
        self.ingress = spec.ingress
        self.livekit_url = spec.livekit_url
        self.livekit_api_key = spec.livekit_api_key
        self.livekit_api_secret = spec.livekit_api_secret
        self.livekit_agent_name = spec.livekit_agent_name
        self.database = pgdatabase_database.DatabaseRequest(spec.storage)


class Calls(ts.Component):
    class Client:
        def __init__(
            self, call_service: application.CallService, call_events_service: application.CallEventsService
        ) -> None:
            self._call_service = call_service
            self._call_events_service = call_events_service

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

    def __init__(self, config: Config, database: pgdatabase_database.Database) -> None:
        self._postgres_call_store = repositories.PostgresCallStore(database)
        self._async_client = httpx.AsyncClient(base_url=config.ingress, timeout=_INGRESS_TIMEOUT)
        self.call_actions_service: restate.Service = restate.Service(
            "CallActions", invocation_retry_policy=_RETRY_POLICY
        )
        self.dialing_actions_service: restate.Service = restate.Service(
            "DialingActions", invocation_retry_policy=_RETRY_POLICY
        )
        self.speech_actions_service: restate.Service = restate.Service(
            "SpeechActions", invocation_retry_policy=_RETRY_POLICY
        )
        self.call_orchestrator_workflow: restate.Workflow = restate.Workflow(
            "CallOrchestrator", invocation_retry_policy=_RETRY_POLICY
        )
        dialing_actions = application.DialingActions(
            gateways.LivekitDialing(
                livekit_api.LiveKitAPI,
                config.livekit_url,
                config.livekit_api_key,
                config.livekit_api_secret,
                config.livekit_agent_name,
            )
        )
        restate_record_call = a.RestateRecordCall(
            self.call_actions_service, application.CallActions(self._postgres_call_store)
        )
        restate_dial_person = a.RestateDialPerson(self.dialing_actions_service, dialing_actions)
        restate_hang_up = a.RestateHangUp(self.dialing_actions_service, dialing_actions)
        restate_say_utterance = a.RestateSayUtterance(
            self.speech_actions_service,
            application.SpeechActions(
                gateways.LivekitSpeech(
                    gateways.LivekitAgentRpc(
                        livekit_rtc.Room,
                        config.livekit_url,
                        config.livekit_api_key,
                        config.livekit_api_secret,
                        config.livekit_agent_name,
                    )
                )
            ),
        )
        restate_conduct_call = b.RestateConductCall(
            self.call_orchestrator_workflow,
            restate_record_call,
            restate_dial_person,
            restate_hang_up,
            restate_say_utterance,
        )
        restate_person_joined = c.RestatePersonJoined(self.call_orchestrator_workflow)
        restate_person_turn_completed = c.RestatePersonTurnCompleted(self.call_orchestrator_workflow)
        restate_ingress_call_orchestrator_relay = c.RestateIngressCallOrchestratorRelay(
            restate_client.Client(self._async_client),
            restate_conduct_call,
            restate_person_joined,
            restate_person_turn_completed,
        )
        self.client: client.CallsClient = Calls.Client(
            application.CallService(restate_ingress_call_orchestrator_relay, self._postgres_call_store),
            application.CallEventsService(restate_ingress_call_orchestrator_relay),
        )

    async def close(self) -> None:
        await self._async_client.aclose()
