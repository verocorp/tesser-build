from __future__ import annotations

import tesser.testing as ts

import alpha.application.ports.beta_check as beta_check
import alpha.component.component as component
import alpha.component.config as config
import pgdatabase.database as pgdatabase


@ts.fake
class FakeBetaCheck(beta_check.BetaCheck):

    async def check(self, request: beta_check.CheckRequest) -> beta_check.CheckResponse:
        return beta_check.CheckResponse(verdict=beta_check.Verdict.OK)


class TestAlpha:

    async def test_a_postgres_coordinate_wires_a_client_over_the_given_database_without_connecting(self) -> None:
        cfg = config.Config(config.Spec(storage="postgres://nobody@nowhere/none"))
        wired = component.Alpha(cfg, pgdatabase.Database(cfg.database), FakeBetaCheck())
        client = wired.client
        await wired.close()
        assert client is wired.client
