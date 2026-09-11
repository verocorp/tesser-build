from __future__ import annotations

import pytest

import tesser.testing as ts

import alpha.application.ports as ports
import alpha.component as component
import pgdatabase.database as pgdatabase_database


@ts.fake
class FakeBetaCheck(ports.BetaCheck):

    async def check(self, check_request: ports.CheckRequest) -> ports.CheckResponse:
        return ports.CheckResponse(verdict=ports.Verdict.OK)


class TestConfig:

    def test_a_postgres_coordinate_requests_that_database(self) -> None:
        config = component.Config(component.Spec(storage="postgres://a@b/c"))
        assert config.storage == "postgres://a@b/c"
        assert config.database == pgdatabase_database.DatabaseRequest("postgres://a@b/c")

    def test_an_unknown_coordinate_is_refused(self) -> None:
        with pytest.raises(ValueError):
            component.Config(component.Spec(storage="sqlite"))


class TestAlpha:

    async def test_a_postgres_coordinate_wires_a_client_over_the_given_database_without_connecting(self) -> None:
        config = component.Config(component.Spec(storage="postgres://nobody@nowhere/none"))
        alpha = component.Alpha(config, pgdatabase_database.Database(config.database), FakeBetaCheck())
        alpha_client = alpha.client
        await alpha.close()
        assert alpha_client is alpha.client
