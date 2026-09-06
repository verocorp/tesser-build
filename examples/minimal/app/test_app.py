from __future__ import annotations

import os

import tesser.testing as ts

import alpha.client as client
import alpha.component as alpha_component
import app as app
import beta.component as beta_component


@ts.fake
class FakeConfigRepository(app.AppConfigRepository):

    def get(self) -> app.AppConfig:
        spec = app.Spec(alpha_component.Config(alpha_component.Spec("memory")), beta_component.Config(beta_component.Spec("a")))
        return app.AppConfig(spec)


class TestAppConfig:

    def test_a_config_carries_each_component_config(self) -> None:
        spec = app.Spec(alpha_component.Config(alpha_component.Spec("memory")), beta_component.Config(beta_component.Spec("k")))
        app_config = app.AppConfig(spec)
        assert app_config.beta is spec.beta


class TestEnvConfigRepository:

    def test_the_environment_is_read_into_a_config(self) -> None:
        os.environ.update(ALPHA_STORAGE="memory", BETA_KEY="k")
        app_config = app.EnvConfigRepository().get()
        assert app_config.beta.key == "k"


class TestApp:

    def test_the_app_wires_alpha_through_beta(self) -> None:
        spec = app.Spec(alpha_component.Config(alpha_component.Spec("memory")), beta_component.Config(beta_component.Spec("a")))
        minimal_app = app.MinimalApp(app.AppConfig(spec))
        add_response = minimal_app.alpha.client.add(client.AddRequest(name="a", part="p"))
        assert add_response.name == "a"


class TestAppLoader:

    def test_the_loader_builds_an_app_from_its_repository(self) -> None:
        app_loader = app.AppLoader(FakeConfigRepository())
        minimal_app = app_loader.load()
        add_response = minimal_app.alpha.client.add(client.AddRequest(name="a", part="p"))
        assert add_response.name == "a"
