from __future__ import annotations

import os

import tesser.testing as ts

import alpha.adapters.handlers.cli as cli
import alpha.application.ports.beta_check as beta_check
import alpha.client.client as client
import alpha.component.component as component
import alpha.component.config as config
import pgdatabase.database as pgdatabase
import protocol.cli as protocol_cli


@ts.fake
class FakeBetaCheck(beta_check.BetaCheck):

    async def check(self, request: beta_check.CheckRequest) -> beta_check.CheckResponse:
        return beta_check.CheckResponse(verdict=beta_check.Verdict.OK)


class TestAlphaContext:

    async def test_a_cli_add_reaches_the_wired_service_and_the_widget_is_stored(self) -> None:
        cfg = config.Config(config.Spec(storage=os.environ["ALPHA_STORAGE"]))
        database = pgdatabase.Database(cfg.database)
        await database.open()
        wired = component.Alpha(cfg, database, FakeBetaCheck())
        response = await cli.Handler(wired.client).add(protocol_cli.CliRequest(args=("ctx-alpha", "p")))
        found = await wired.client.find(client.FindRequest(name="ctx-alpha"))
        missing = await wired.client.find(client.FindRequest(name="ctx-alpha-never-added"))
        await wired.close()
        await database.close()
        assert response.line.text == "ctx-alpha"
        assert found.found == "yes"
        assert missing.found == "no"

    async def test_a_taken_part_is_stored_and_read_back_through_the_client(self) -> None:
        cfg = config.Config(config.Spec(storage=os.environ["ALPHA_STORAGE"]))
        database = pgdatabase.Database(cfg.database)
        await database.open()
        wired = component.Alpha(cfg, database, FakeBetaCheck())
        await wired.client.add(client.AddRequest(name="ctx-alpha-taken", part="p"))
        taken = await wired.client.take(client.TakeRequest(name="ctx-alpha-taken", part="q"))
        retaken = await wired.client.take(client.TakeRequest(name="ctx-alpha-taken", part="q"))
        await wired.close()
        await database.close()
        assert taken.part == "q"
        assert retaken.part == "q"
