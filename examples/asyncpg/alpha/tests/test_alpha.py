from __future__ import annotations

import os

import pytest

import tesser.testing as ts

import alpha.adapters.handlers as handlers
import alpha.application.ports as ports
import alpha.client as client
import alpha.component as component
import pgdatabase.database as pgdatabase_database
import protocol


@ts.fake
class FakeBetaCheck(ports.BetaCheck):

    async def check_name(self, check_name_request: ports.CheckNameRequest) -> ports.CheckNameResponse:
        return ports.CheckNameResponse(outcome=ports.CheckNameOutcome.OK)


@ts.fake
class FakeRefusingBetaCheck(ports.BetaCheck):

    async def check_name(self, check_name_request: ports.CheckNameRequest) -> ports.CheckNameResponse:
        return ports.CheckNameResponse(outcome=ports.CheckNameOutcome.REFUSED)


class TestAlphaContext:

    async def test_a_cli_add_reaches_the_wired_service_and_the_widget_is_stored(self) -> None:
        config = component.Config(component.Spec(storage=os.environ["ALPHA_STORAGE"]))
        database = pgdatabase_database.Database(config.database)
        await database.open()
        async with database.acquire() as connection:
            await connection.execute("DROP TABLE IF EXISTS widgets")
        alpha = component.Alpha(config, database, FakeBetaCheck())
        cli_response = await handlers.Handler(alpha.client).add(
            protocol.CliRequest(args=("ctx-alpha", "p"))
        )
        found = await alpha.client.find_widget(client.FindWidgetRequest(name="ctx-alpha"))
        missing = await alpha.client.find_widget(
            client.FindWidgetRequest(name="ctx-alpha-never-added")
        )
        await alpha.close()
        await database.close()
        assert cli_response.line.text == "ctx-alpha p kept"
        assert found.found == "yes"
        assert missing.found == "no"

    async def test_a_taken_part_is_stored_and_read_back_through_the_client(self) -> None:
        config = component.Config(component.Spec(storage=os.environ["ALPHA_STORAGE"]))
        database = pgdatabase_database.Database(config.database)
        await database.open()
        async with database.acquire() as connection:
            await connection.execute("DROP TABLE IF EXISTS widgets")
        alpha = component.Alpha(config, database, FakeBetaCheck())
        await alpha.client.add_part(client.AddPartRequest(name="ctx-alpha-taken", part="p"))
        taken = await alpha.client.take_part(
            client.TakePartRequest(name="ctx-alpha-taken", part="q")
        )
        retaken = await alpha.client.take_part(
            client.TakePartRequest(name="ctx-alpha-taken", part="q")
        )
        await alpha.close()
        await database.close()
        assert taken.part == "q"
        assert retaken.part == "q"

    async def test_adding_a_stored_name_conflicts_and_the_stored_standing_survives(self) -> None:
        config = component.Config(component.Spec(storage=os.environ["ALPHA_STORAGE"]))
        database = pgdatabase_database.Database(config.database)
        await database.open()
        async with database.acquire() as connection:
            await connection.execute("DROP TABLE IF EXISTS widgets")
        alpha = component.Alpha(config, database, FakeRefusingBetaCheck())
        add_part_response = await alpha.client.add_part(
            client.AddPartRequest(name="ctx-alpha-twice", part="ctx-alpha-twice")
        )
        with pytest.raises(client.Conflict) as caught:
            await alpha.client.add_part(client.AddPartRequest(name="ctx-alpha-twice", part="q"))
        take_part_response = await alpha.client.take_part(
            client.TakePartRequest(name="ctx-alpha-twice", part="ctx-alpha-twice")
        )
        await alpha.close()
        await database.close()
        assert add_part_response.standing == "released"
        assert caught.value.code == "widget_exists"
        assert take_part_response.standing == "released"
