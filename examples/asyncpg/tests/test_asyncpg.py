from __future__ import annotations

import os

import asyncpg

import alpha.client.client as alpha_client
import app.loader as loader
import beta.client.client as beta_client


class TestPostgresBackedApp:

    async def test_the_loaded_app_writes_both_contexts_to_postgres(self) -> None:
        dsn = os.environ["ASYNCPG_DSN"]
        connection = await asyncpg.connect(dsn)
        await connection.execute("DROP TABLE IF EXISTS widgets, keys")
        os.environ.update(ALPHA_STORAGE=dsn, BETA_STORAGE=dsn)
        built = loader.load()
        held = await built.beta.client.hold(beta_client.HoldRequest(key="a"))
        taken = await built.alpha.client.add(alpha_client.AddRequest(name="b", part="p"))
        checked = await built.alpha.client.add(alpha_client.AddRequest(name="a", part="a"))
        await built.close()
        widgets = await connection.fetch("SELECT name FROM widgets ORDER BY name")
        keys = await connection.fetch("SELECT key FROM keys ORDER BY key")
        await connection.close()
        assert held.key == "a"
        assert taken.name == "b"
        assert checked.name == "a"
        assert [row["name"] for row in widgets] == ["b"]
        assert [row["key"] for row in keys] == ["a"]

    async def test_a_second_load_reads_what_the_first_wrote(self) -> None:
        dsn = os.environ["ASYNCPG_DSN"]
        connection = await asyncpg.connect(dsn)
        await connection.execute("DROP TABLE IF EXISTS widgets, keys")
        await connection.close()
        os.environ.update(ALPHA_STORAGE=dsn, BETA_STORAGE=dsn)
        first = loader.load()
        await first.beta.client.hold(beta_client.HoldRequest(key="k"))
        await first.close()
        second = loader.load()
        checked = await second.beta.client.check(beta_client.CheckRequest(key="k"))
        await second.close()
        assert checked.held == "yes"
