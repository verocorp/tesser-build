from __future__ import annotations

import os

import pytest

import tesser.testing as ts

import alpha.adapters.handlers as handlers
import alpha.application.ports as ports
import alpha.client as client
import alpha.component as component
import pgdatabase.database as pgdatabase
import protocol
import tesser.errors as errors


@ts.fake
class FakeBetaCheck(ports.BetaCheck):

    async def check(self, check_request: ports.CheckRequest) -> ports.CheckResponse:
        return ports.CheckResponse(verdict=ports.Verdict.OK)


@ts.fake
class FakeRefusingBetaCheck(ports.BetaCheck):

    async def check(self, check_request: ports.CheckRequest) -> ports.CheckResponse:
        return ports.CheckResponse(verdict=ports.Verdict.REFUSED)


class TestAlphaContext:

    async def test_a_cli_add_reaches_the_wired_service_and_the_widget_is_stored(self) -> None:
        config = component.Config(component.Spec(storage=os.environ["ALPHA_STORAGE"]))
        database = pgdatabase.Database(config.database)
        await database.open()
        async with database.acquire() as connection:
            await connection.execute("DROP TABLE IF EXISTS widgets")
        alpha = component.Alpha(config, database, FakeBetaCheck())
        cli_response = await handlers.Handler(alpha.client).add(
            protocol.CliRequest(args=("ctx-alpha", "p"))
        )
        found = await alpha.client.find(client.FindRequest(name="ctx-alpha"))
        missing = await alpha.client.find(client.FindRequest(name="ctx-alpha-never-added"))
        await alpha.close()
        await database.close()
        assert cli_response.line.text == "ctx-alpha p kept"
        assert found.found == "yes"
        assert missing.found == "no"

    async def test_a_taken_part_is_stored_and_read_back_through_the_client(self) -> None:
        config = component.Config(component.Spec(storage=os.environ["ALPHA_STORAGE"]))
        database = pgdatabase.Database(config.database)
        await database.open()
        async with database.acquire() as connection:
            await connection.execute("DROP TABLE IF EXISTS widgets")
        alpha = component.Alpha(config, database, FakeBetaCheck())
        await alpha.client.add(client.AddRequest(name="ctx-alpha-taken", part="p"))
        taken = await alpha.client.take(client.TakeRequest(name="ctx-alpha-taken", part="q"))
        retaken = await alpha.client.take(client.TakeRequest(name="ctx-alpha-taken", part="q"))
        await alpha.close()
        await database.close()
        assert taken.part == "q"
        assert retaken.part == "q"

    async def test_adding_a_stored_name_conflicts_and_the_stored_standing_survives(self) -> None:
        config = component.Config(component.Spec(storage=os.environ["ALPHA_STORAGE"]))
        database = pgdatabase.Database(config.database)
        await database.open()
        async with database.acquire() as connection:
            await connection.execute("DROP TABLE IF EXISTS widgets")
        alpha = component.Alpha(config, database, FakeRefusingBetaCheck())
        add_response = await alpha.client.add(
            client.AddRequest(name="ctx-alpha-twice", part="ctx-alpha-twice")
        )
        with pytest.raises(errors.DomainError) as caught:
            await alpha.client.add(client.AddRequest(name="ctx-alpha-twice", part="q"))
        take_response = await alpha.client.take(
            client.TakeRequest(name="ctx-alpha-twice", part="ctx-alpha-twice")
        )
        await alpha.close()
        await database.close()
        assert add_response.standing == "released"
        assert caught.value.kind is errors.Kind.CONFLICT
        assert take_response.standing == "released"
