from __future__ import annotations

import calls.component as component
import pgdatabase.database as pgdatabase_database


class TestConfig:

    def test_a_postgres_coordinate_requests_that_database(self) -> None:
        spec = component.Spec(storage="postgres://a@b/c")

        config = component.Config(spec)

        assert config.database == pgdatabase_database.DatabaseRequest(spec.storage)


class TestCalls:

    async def test_a_postgres_coordinate_wires_a_client_over_the_given_database_without_connecting(self) -> None:
        config = component.Config(component.Spec(storage="postgres://nobody@nowhere/none"))

        calls = component.Calls(config, pgdatabase_database.Database(config.database))
        calls_client = calls.client
        await calls.close()

        assert calls_client is calls.client
