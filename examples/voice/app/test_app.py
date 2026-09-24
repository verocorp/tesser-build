from __future__ import annotations

import os

import tesser.testing as ts

import app
import calls.client as calls_client
import calls.component as calls_component


@ts.helper
def calls_spec(storage: str = "postgres://a@b/calls", restate_url: str = "http://localhost:8080") -> calls_component.Spec:
    return calls_component.Spec(
        storage=storage,
        restate_url=restate_url,
        livekit_url="ws://livekit",
        livekit_api_key="key",
        livekit_api_secret="secret",
        livekit_agent_name="caller",
    )


@ts.fake
class FakeConfigRepository(app.AppConfigRepository):

    def get(self) -> app.AppConfig:
        return app.AppConfig(
            app.Spec(
                calls_component.Config(
                    calls_spec(storage=os.environ["CALLS_STORAGE"], restate_url=os.environ["RESTATE_URL"])
                )
            )
        )


class TestAppConfig:

    def test_a_config_carries_the_calls_config(self) -> None:
        spec = app.Spec(calls_component.Config(calls_spec()))

        app_config = app.AppConfig(spec)

        assert app_config.calls is spec.calls


class TestEnvConfigRepository:

    def test_the_environment_is_read_into_a_config(self) -> None:
        app_config = app.EnvConfigRepository().get()

        assert app_config.calls.storage == os.environ["CALLS_STORAGE"]
        assert app_config.calls.restate_url == os.environ["RESTATE_URL"]
        assert app_config.calls.livekit_url == os.environ["LIVEKIT_URL"]
        assert app_config.calls.livekit_agent_name == os.environ["LIVEKIT_AGENT_NAME"]


class TestAppLoader:

    async def test_the_loader_builds_an_app_whose_client_can_look_up_a_call(self) -> None:
        voice_app = app.AppLoader(FakeConfigRepository()).load()
        await voice_app.open()

        raised: list[calls_client.CallNotFound] = []
        try:
            await voice_app.calls.client.get_call(calls_client.GetCallRequest(call_id="app-never-placed"))
        except calls_client.CallNotFound as call_not_found:
            raised.append(call_not_found)
        await voice_app.close()

        assert [str(call_not_found) for call_not_found in raised] == ["no call 'app-never-placed'"]
