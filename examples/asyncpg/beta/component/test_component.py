from __future__ import annotations

import pytest

import beta.component as component
import pgdatabase.database as pgdatabase


class TestConfig:

    def test_a_postgres_coordinate_requests_that_database(self) -> None:
        config = component.Config(component.Spec(storage="postgres://a@b/c"))
        assert config.storage == "postgres://a@b/c"
        assert config.database == pgdatabase.DatabaseRequest("postgres://a@b/c")

    def test_an_unknown_coordinate_is_refused(self) -> None:
        with pytest.raises(ValueError):
            component.Config(component.Spec(storage="sqlite"))


class TestBeta:

    async def test_a_postgres_coordinate_wires_a_client_over_the_given_database_without_connecting(self) -> None:
        config = component.Config(component.Spec(storage="postgres://nobody@nowhere/none"))
        beta = component.Beta(config, pgdatabase.Database(config.database))
        beta_client = beta.client
        await beta.close()
        assert beta_client is beta.client
