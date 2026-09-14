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
        hold_key_response = await asyncpg_app.beta.client.hold_key(
            beta_client.HoldKeyRequest(key="e2e-held")
        )
        checked = await asyncpg_app.beta.client.check_key(
            beta_client.CheckKeyRequest(key="e2e-held")
        )
        unheld = await asyncpg_app.beta.client.check_key(
            beta_client.CheckKeyRequest(key="e2e-never-held")
        )
        taken = await asyncpg_app.alpha.client.add_part(
            alpha_client.AddPartRequest(name="e2e-taken", part="p")
        )
        found = await asyncpg_app.alpha.client.find_widget(
            alpha_client.FindWidgetRequest(name="e2e-taken")
        )
        missing = await asyncpg_app.alpha.client.find_widget(
            alpha_client.FindWidgetRequest(name="e2e-never-added")
        )
        kept = await asyncpg_app.alpha.client.add_part(
            alpha_client.AddPartRequest(name="e2e-held", part="e2e-held")
        )
        cleared = await asyncpg_app.alpha.client.find_widget(
            alpha_client.FindWidgetRequest(name="e2e-held")
        )
        dropped = await asyncpg_app.alpha.client.add_part(
            alpha_client.AddPartRequest(name="e2e-never-held", part="e2e-never-held")
        )
        refused = await asyncpg_app.alpha.client.find_widget(
            alpha_client.FindWidgetRequest(name="e2e-never-held")
        )
        reloaded = await asyncpg_app.alpha.client.take_part(
            alpha_client.TakePartRequest(name="e2e-never-held", part="q")
        )
        retaken = await asyncpg_app.alpha.client.take_part(
            alpha_client.TakePartRequest(name="e2e-taken", part="q")
        )
        await asyncpg_app.close()
        assert hold_key_response.key == "e2e-held"
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
