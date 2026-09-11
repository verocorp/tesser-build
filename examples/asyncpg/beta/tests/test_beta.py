from __future__ import annotations

import os

import beta.client as client
import beta.component as component
import pgdatabase.database as pgdatabase_database


class TestBetaContext:

    async def test_a_held_key_is_reported_held_and_an_unknown_key_is_not(self) -> None:
        config = component.Config(component.Spec(storage=os.environ["BETA_STORAGE"]))
        database = pgdatabase_database.Database(config.database)
        await database.open()
        beta = component.Beta(config, database)
        hold_response = await beta.client.hold(client.HoldRequest(key="ctx-beta"))
        checked = await beta.client.check(client.CheckRequest(key="ctx-beta"))
        unknown = await beta.client.check(client.CheckRequest(key="ctx-beta-never-held"))
        await beta.close()
        await database.close()
        assert hold_response.key == "ctx-beta"
        assert checked.held == "yes"
        assert unknown.held == "no"
