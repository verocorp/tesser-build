from __future__ import annotations

import os

import alpha.client.client as alpha_client
import alpha.component.config as alpha_config
import app.app as app_module
import app.config as config
import beta.client.client as beta_client
import beta.component.config as beta_config


class TestApp:

    async def test_two_contexts_on_one_dsn_share_one_database_and_alpha_reaches_beta(self) -> None:
        dsn = os.environ["ALPHA_STORAGE"]
        spec = config.Spec(alpha_config.Config(alpha_config.Spec(dsn)), beta_config.Config(beta_config.Spec(dsn)))
        app = app_module.App(config.Config(spec))
        await app.open()
        await app.beta.client.hold(beta_client.HoldRequest(key="shared"))
        added = await app.alpha.client.add(alpha_client.AddRequest(name="shared", part="p"))
        await app.close()
        assert added.name == "shared"
        assert len(app.databases) == 1

    async def test_two_dsns_give_two_databases(self) -> None:
        spec = config.Spec(
            alpha_config.Config(alpha_config.Spec("postgres://nobody@nowhere/alpha")),
            beta_config.Config(beta_config.Spec("postgres://nobody@nowhere/beta")),
        )
        app = app_module.App(config.Config(spec))
        await app.close()
        assert len(app.databases) == 2
