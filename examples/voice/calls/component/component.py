from __future__ import annotations

import tesser.component as ts
import livekit.api as livekit_api
import livekit.rtc as livekit_rtc

import calls.adapters.gateways as gateways
import calls.adapters.repositories as repositories
import calls.adapters.runners as runners
import calls.adapters.runtimes as runtimes
import calls.application as application
import calls.client as client
import pgdatabase.database as pgdatabase_database


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
        self.restate_call_runtime: runtimes.RestateCallRuntime = runtimes.RestateCallRuntime(
            application.CallActions(self._postgres_call_store),
            application.DialingActions(
                gateways.LivekitDialing(
                    livekit_api.LiveKitAPI,
                    config.livekit_url,
                    config.livekit_api_key,
                    config.livekit_api_secret,
                    config.livekit_agent_name,
                )
            ),
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
            runners.RestateCallWorkflow(),
        )
        self.client: client.CallsClient = Calls.Client(
            application.CallService(
                runners.RestateIngressCallOrchestratorRelay(config.ingress),
                self._postgres_call_store,
            ),
            application.CallEventsService(
                runners.RestateIngressCallOrchestratorRelay(config.ingress)
            ),
        )

    async def close(self) -> None:
        return None
