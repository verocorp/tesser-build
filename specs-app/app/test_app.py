from __future__ import annotations

import os

import pytest

import tesser.testing as ts

import app as app
import specification.client as client
import specification.component as component
import tesser.errors as errors


@ts.fake
class FakeConfigRepository(app.AppConfigRepository):

    def get(self) -> app.AppConfig:
        spec = app.Spec(
            specification=component.Config(component.Spec("memory")),
            http=app.HttpConfig(app.HttpSpec(host="127.0.0.1", port=0)),
        )
        return app.AppConfig(spec)


@ts.helper
def app_spec(storage: str = "memory", host: str = "127.0.0.1", port: int = 0) -> app.Spec:
    return app.Spec(
        specification=component.Config(component.Spec(storage)),
        http=app.HttpConfig(app.HttpSpec(host=host, port=port)),
    )


class TestAppConfig:

    def test_a_config_carries_each_part(self) -> None:
        spec = app_spec(port=8080)
        app_config = app.AppConfig(spec)
        assert app_config.specification is spec.specification
        assert app_config.http.port == 8080


class TestEnvConfigRepository:

    def test_the_environment_is_read_into_a_config(self) -> None:
        os.environ.update(SPECIFICATION_STORAGE="memory", HTTP_HOST="127.0.0.1", HTTP_PORT="8080")
        app_config = app.EnvConfigRepository().get()
        assert app_config.specification.storage == "memory"
        assert app_config.http.host == "127.0.0.1"
        assert app_config.http.port == 8080

    def test_a_port_that_is_not_a_number_is_refused(self) -> None:
        os.environ.update(SPECIFICATION_STORAGE="memory", HTTP_HOST="127.0.0.1", HTTP_PORT="eighty")
        with pytest.raises(errors.DomainError) as caught:
            app.EnvConfigRepository().get()
        assert caught.value.code == "bad_http_port"


class TestApp:

    def test_the_app_wires_the_specification_context(self) -> None:
        specs_app = app.SpecsApp(app.AppConfig(app_spec()))
        add_story_response = specs_app.specification.client.add_story(
            client.AddStoryRequest(jtbd_id="j-root", given="g", when="w", then="t")
        )
        assert add_story_response.story_id == "j-root-s0"


class TestAppLoader:

    def test_the_loader_builds_an_app_from_its_repository(self) -> None:
        specs_app = app.AppLoader(FakeConfigRepository()).load()
        add_story_response = specs_app.specification.client.add_story(
            client.AddStoryRequest(jtbd_id="j-root", given="g", when="w", then="t")
        )
        assert add_story_response.story_id == "j-root-s0"
