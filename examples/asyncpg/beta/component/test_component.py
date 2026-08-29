from __future__ import annotations

import beta.component.component as component
import beta.component.config as config
import pgdatabase.database as pgdatabase


class TestBeta:

    async def test_a_postgres_coordinate_wires_a_client_over_the_given_database_without_connecting(self) -> None:
        cfg = config.Config(config.Spec(storage="postgres://nobody@nowhere/none"))
        wired = component.Beta(cfg, pgdatabase.Database(cfg.database))
        client = wired.client
        await wired.close()
        assert client is wired.client
