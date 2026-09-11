from __future__ import annotations

import os

import alpha.client as alpha_client
import app
import beta.client as beta_client
import pgdatabase.database as pgdatabase_database


class TestLoadedApp:

    async def test_the_loaded_app_writes_and_reads_both_contexts(self) -> None:
        database = pgdatabase_database.Database(pgdatabase_database.DatabaseRequest(os.environ["ALPHA_STORAGE"]))
        await database.open()
        async with database.acquire() as connection:
            await connection.execute("DROP TABLE IF EXISTS widgets")
        await database.close()
        asyncpg_app = app.load()
        await asyncpg_app.open()
        hold_response = await asyncpg_app.beta.client.hold(beta_client.HoldRequest(key="e2e-held"))
        checked = await asyncpg_app.beta.client.check(beta_client.CheckRequest(key="e2e-held"))
        unheld = await asyncpg_app.beta.client.check(beta_client.CheckRequest(key="e2e-never-held"))
        taken = await asyncpg_app.alpha.client.add(alpha_client.AddRequest(name="e2e-taken", part="p"))
        found = await asyncpg_app.alpha.client.find(alpha_client.FindRequest(name="e2e-taken"))
        missing = await asyncpg_app.alpha.client.find(alpha_client.FindRequest(name="e2e-never-added"))
        kept = await asyncpg_app.alpha.client.add(alpha_client.AddRequest(name="e2e-held", part="e2e-held"))
        cleared = await asyncpg_app.alpha.client.find(alpha_client.FindRequest(name="e2e-held"))
        dropped = await asyncpg_app.alpha.client.add(
            alpha_client.AddRequest(name="e2e-never-held", part="e2e-never-held")
        )
        refused = await asyncpg_app.alpha.client.find(alpha_client.FindRequest(name="e2e-never-held"))
        reloaded = await asyncpg_app.alpha.client.take(
            alpha_client.TakeRequest(name="e2e-never-held", part="q")
        )
        retaken = await asyncpg_app.alpha.client.take(
            alpha_client.TakeRequest(name="e2e-taken", part="q")
        )
        await asyncpg_app.close()
        assert hold_response.key == "e2e-held"
        assert checked.held == "yes"
        assert unheld.held == "no"
        assert taken.name == "e2e-taken"
        assert found.found == "yes"
        assert missing.found == "no"
        assert kept.name == "e2e-held"
        assert kept.standing == "kept"
        assert cleared.found == "yes"
        assert dropped.name == "e2e-never-held"
        assert dropped.standing == "released"
        assert refused.found == "yes"
        assert reloaded.standing == "released"
        assert retaken.part == "q"
