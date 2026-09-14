from __future__ import annotations

import os

import tesser.testing as ts

import app
import calls.client as calls_client
import calls.component as calls_component


@ts.fake
class FakeConfigRepository(app.AppConfigRepository):

    def get(self) -> app.AppConfig:
        calls_storage = os.environ["CALLS_STORAGE"]
        return app.AppConfig(app.Spec(calls_component.Config(calls_component.Spec(calls_storage))))


class TestAppConfig:

    def test_a_config_carries_the_calls_config(self) -> None:
        spec = app.Spec(calls_component.Config(calls_component.Spec("postgres://a@b/calls")))

        app_config = app.AppConfig(spec)

        assert app_config.calls is spec.calls


class TestEnvConfigRepository:

    def test_the_environment_is_read_into_a_config(self) -> None:
        app_config = app.EnvConfigRepository().get()

        assert app_config.calls.storage == os.environ["CALLS_STORAGE"]


class TestAppLoader:

    async def test_the_loader_builds_an_app_whose_client_places_a_call(self) -> None:
        voice_app = app.AppLoader(FakeConfigRepository()).load()
        await voice_app.open()

        place_call_response = await voice_app.calls.client.place_call(
            calls_client.PlaceCallRequest(person_name="Ada", phone_number="+15555550100")
        )
        await voice_app.close()

        assert place_call_response.call_id != ""
