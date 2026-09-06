from __future__ import annotations

import os

import tesser.testing as ts

import alpha.client as alpha_client
import alpha.component as alpha_component
import app
import beta.client as beta_client
import beta.component as beta_component


@ts.fake
class FakeConfigRepository(app.AppConfigRepository):

    def get(self) -> app.AppConfig:
        alpha_storage = os.environ["ALPHA_STORAGE"]
        beta_storage = os.environ["BETA_STORAGE"]
        spec = app.Spec(
            alpha_component.Config(alpha_component.Spec(alpha_storage)),
            beta_component.Config(beta_component.Spec(beta_storage)),
        )
        return app.AppConfig(spec)


class TestAppConfig:

    def test_a_config_carries_each_component_config(self) -> None:
        spec = app.Spec(
            alpha_component.Config(alpha_component.Spec("postgres://a@b/alpha")),
            beta_component.Config(beta_component.Spec("postgres://a@b/beta")),
        )
        app_config = app.AppConfig(spec)
        assert app_config.beta is spec.beta


class TestEnvConfigRepository:

    def test_the_environment_is_read_into_a_config(self) -> None:
        app_config = app.EnvConfigRepository().get()
        assert app_config.alpha.storage == os.environ["ALPHA_STORAGE"]
        assert app_config.beta.storage == os.environ["BETA_STORAGE"]


class TestApp:

    async def test_two_contexts_on_one_dsn_share_one_database_and_alpha_reaches_beta(self) -> None:
        dsn = os.environ["ALPHA_STORAGE"]
        spec = app.Spec(
            alpha_component.Config(alpha_component.Spec(dsn)),
            beta_component.Config(beta_component.Spec(dsn)),
        )
        asyncpg_app = app.AsyncpgApp(app.AppConfig(spec))
        await asyncpg_app.open()
        await asyncpg_app.beta.client.hold(beta_client.HoldRequest(key="shared"))
        add_response = await asyncpg_app.alpha.client.add(
            alpha_client.AddRequest(name="shared", part="p")
        )
        await asyncpg_app.close()
        assert add_response.name == "shared"
        assert len(asyncpg_app.databases) == 1

    async def test_two_dsns_give_two_databases(self) -> None:
        spec = app.Spec(
            alpha_component.Config(alpha_component.Spec("postgres://nobody@nowhere/alpha")),
            beta_component.Config(beta_component.Spec("postgres://nobody@nowhere/beta")),
        )
        asyncpg_app = app.AsyncpgApp(app.AppConfig(spec))
        await asyncpg_app.close()
        assert len(asyncpg_app.databases) == 2


class TestAppLoader:

    async def test_the_loader_builds_an_app_from_its_repository(self) -> None:
        asyncpg_app = app.AppLoader(FakeConfigRepository()).load()
        await asyncpg_app.open()
        add_response = await asyncpg_app.alpha.client.add(
            alpha_client.AddRequest(name="loader-a", part="p")
        )
        await asyncpg_app.close()
        assert add_response.name == "loader-a"
