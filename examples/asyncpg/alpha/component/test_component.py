from __future__ import annotations

import pytest

import tesser.testing as ts

import alpha.application.ports.beta_check as beta_check
import alpha.client.client as client
import alpha.component.component as component
import alpha.component.config as config
import pgdatabase.database as pgdatabase
import tesser.errors as errors


@ts.fake
class FakeBetaCheck(beta_check.BetaCheck):

    async def check(self, request: beta_check.CheckRequest) -> beta_check.CheckResponse:
        return beta_check.CheckResponse(verdict=beta_check.Verdict.OK)


class TestAlpha:

    async def test_the_memory_coordinate_wires_a_client_that_adds_a_widget(self) -> None:
        wired = component.Alpha(config.Config(config.Spec(storage="memory")), None, FakeBetaCheck())
        added = await wired.client.add(client.AddRequest(name="a", part="p"))
        await wired.close()
        assert added.name == "a"

    async def test_a_postgres_coordinate_wires_over_the_given_database_without_connecting(self) -> None:
        cfg = config.Config(config.Spec(storage="postgres://nobody@nowhere/none"))
        assert cfg.database is not None
        wired = component.Alpha(cfg, pgdatabase.Database(cfg.database), FakeBetaCheck())
        await wired.close()

    def test_a_postgres_coordinate_without_a_database_is_refused(self) -> None:
        with pytest.raises(errors.DomainError) as caught:
            component.Alpha(config.Config(config.Spec(storage="postgres://nobody@nowhere/none")), None, FakeBetaCheck())
        assert caught.value.code == "missing_database"
