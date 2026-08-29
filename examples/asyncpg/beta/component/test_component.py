from __future__ import annotations

import pytest

import beta.client.client as client
import beta.component.component as component
import beta.component.config as config
import pgdatabase.database as pgdatabase
import tesser.errors as errors


class TestBeta:

    async def test_the_memory_coordinate_wires_a_client_that_holds_and_checks(self) -> None:
        wired = component.Beta(config.Config(config.Spec(storage="memory")), None)
        await wired.client.hold(client.HoldRequest(key="k"))
        checked = await wired.client.check(client.CheckRequest(key="k"))
        await wired.close()
        assert checked.held == "yes"

    async def test_a_postgres_coordinate_wires_over_the_given_database_without_connecting(self) -> None:
        cfg = config.Config(config.Spec(storage="postgresql://nobody@nowhere/none"))
        assert cfg.database is not None
        wired = component.Beta(cfg, pgdatabase.Database(cfg.database))
        await wired.close()

    def test_a_postgres_coordinate_without_a_database_is_refused(self) -> None:
        with pytest.raises(errors.DomainError) as caught:
            component.Beta(config.Config(config.Spec(storage="postgresql://nobody@nowhere/none")), None)
        assert caught.value.code == "missing_database"
