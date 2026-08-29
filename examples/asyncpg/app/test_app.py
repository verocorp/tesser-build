from __future__ import annotations

import os

import alpha.client.client as alpha_client
import alpha.component.config as alpha_config
import app.app as app
import app.config as config
import beta.client.client as beta_client
import beta.component.config as beta_config


class TestApp:

    async def test_the_app_wires_alpha_through_beta(self) -> None:
        spec = config.Spec(alpha_config.Config(alpha_config.Spec("memory")), beta_config.Config(beta_config.Spec("memory")))
        built = app.App(config.Config(spec))
        added = await built.alpha.client.add(alpha_client.AddRequest(name="a", part="p"))
        await built.close()
        assert added.name == "a"
        assert built.databases == ()

    async def test_two_contexts_on_one_dsn_share_one_database(self) -> None:
        dsn = os.environ["ALPHA_STORAGE"]
        spec = config.Spec(alpha_config.Config(alpha_config.Spec(dsn)), beta_config.Config(beta_config.Spec(dsn)))
        built = app.App(config.Config(spec))
        await built.beta.client.hold(beta_client.HoldRequest(key="shared"))
        await built.alpha.client.add(alpha_client.AddRequest(name="shared", part="p"))
        await built.close()
        assert len(built.databases) == 1

    async def test_two_dsns_give_two_databases(self) -> None:
        spec = config.Spec(
            alpha_config.Config(alpha_config.Spec("postgres://nobody@nowhere/alpha")),
            beta_config.Config(beta_config.Spec("postgres://nobody@nowhere/beta")),
        )
        built = app.App(config.Config(spec))
        await built.close()
        assert len(built.databases) == 2

    async def test_a_memory_context_beside_a_postgres_one_needs_one_database(self) -> None:
        spec = config.Spec(
            alpha_config.Config(alpha_config.Spec("memory")),
            beta_config.Config(beta_config.Spec("postgres://nobody@nowhere/beta")),
        )
        built = app.App(config.Config(spec))
        await built.close()
        assert len(built.databases) == 1
