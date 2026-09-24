from __future__ import annotations

import os

import tesser.testing as ts

import alpha.client as alpha_client
import alpha.component as alpha_component
import app as app
import beta.component as beta_component


@ts.fake
class FakeConfigRepository(app.AppConfigRepository):

    def get(self) -> app.AppConfig:
        spec = app.Spec(alpha_component.Config(alpha_component.Spec(os.environ["ALPHA_STORAGE"], "http://localhost:8080")), beta_component.Config(beta_component.Spec("a")))
        return app.AppConfig(spec)


class TestAppConfig:

    def test_a_config_carries_each_component_config(self) -> None:
        spec = app.Spec(alpha_component.Config(alpha_component.Spec(os.environ["ALPHA_STORAGE"], "http://localhost:8080")), beta_component.Config(beta_component.Spec("k")))
        app_config = app.AppConfig(spec)
        assert app_config.beta is spec.beta


class TestEnvConfigRepository:

    def test_the_environment_is_read_into_a_config(self) -> None:
        ambient = {name: os.environ.get(name, "") for name in ("ALPHA_STORAGE", "BETA_KEY", "RESTATE_INGRESS")}
        os.environ.update(ALPHA_STORAGE="postgres://a@b/c", BETA_KEY="k", RESTATE_INGRESS="http://ingress.invalid:8080")
        try:
            app_config = app.EnvConfigRepository().get()
        finally:
            os.environ.update(ambient)
        assert (app_config.alpha.storage, app_config.beta.key, app_config.alpha.ingress) == (
            "postgres://a@b/c",
            "k",
            "http://ingress.invalid:8080",
        )


class TestApp:

    async def test_the_app_wires_alpha_through_beta(self) -> None:
        spec = app.Spec(alpha_component.Config(alpha_component.Spec(os.environ["ALPHA_STORAGE"], "http://localhost:8080")), beta_component.Config(beta_component.Spec("a")))
        minimal_app = app.MinimalApp(app.AppConfig(spec))
        add_part_response = await minimal_app.alpha.client.add_part(alpha_client.AddPartRequest(name="a", part="p"))
        assert add_part_response.name == "a"


class TestAppLoader:

    async def test_the_loader_builds_an_app_from_its_repository(self) -> None:
        app_loader = app.AppLoader(FakeConfigRepository())
        minimal_app = app_loader.load()
        add_part_response = await minimal_app.alpha.client.add_part(alpha_client.AddPartRequest(name="a", part="p"))
        assert add_part_response.name == "a"
