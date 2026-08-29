from __future__ import annotations

import os

import beta.client.client as client
import beta.component.component as component
import beta.component.config as config
import pgdatabase.database as pgdatabase


class TestBetaContext:

    async def test_a_held_key_is_reported_held_and_an_unknown_key_is_not(self) -> None:
        cfg = config.Config(config.Spec(storage=os.environ["BETA_STORAGE"]))
        database = pgdatabase.Database(cfg.database)
        await database.open()
        wired = component.Beta(cfg, database)
        held = await wired.client.hold(client.HoldRequest(key="ctx-beta"))
        checked = await wired.client.check(client.CheckRequest(key="ctx-beta"))
        unknown = await wired.client.check(client.CheckRequest(key="ctx-beta-never-held"))
        await wired.close()
        await database.close()
        assert held.key == "ctx-beta"
        assert checked.held == "yes"
        assert unknown.held == "no"
