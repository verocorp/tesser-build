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
        livekit_sip_trunk_id: str,
    ) -> None:
        self.storage = storage
        self.ingress = ingress
        self.livekit_url = livekit_url
        self.livekit_api_key = livekit_api_key
        self.livekit_api_secret = livekit_api_secret
        self.livekit_agent_name = livekit_agent_name
        self.livekit_sip_trunk_id = livekit_sip_trunk_id


class Config(ts.Config):

    def __init__(self, spec: Spec) -> None:
        self.storage = spec.storage
        self.ingress = spec.ingress
        self.livekit_url = spec.livekit_url
        self.livekit_api_key = spec.livekit_api_key
        self.livekit_api_secret = spec.livekit_api_secret
        self.livekit_agent_name = spec.livekit_agent_name
        self.livekit_sip_trunk_id = spec.livekit_sip_trunk_id
        self.database = pgdatabase_database.DatabaseRequest(spec.storage)


class Calls(ts.Component):

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
                    config.livekit_sip_trunk_id,
                )
            ),
            application.SpeechActions(
                gateways.LivekitSpeech(
                    livekit_rtc.Room,
                    config.livekit_url,
                    config.livekit_api_key,
                    config.livekit_api_secret,
                    config.livekit_agent_name,
                )
            ),
        )
        restate_ingress_call_relays = runners.RestateIngressCallRelays(config.ingress, self.restate_call_runtime)
        self.client: client.CallsClient = application.CallService(
            restate_ingress_call_relays,
            restate_ingress_call_relays,
            restate_ingress_call_relays,
            self._postgres_call_store,
        )

    async def close(self) -> None:
        return None
