from __future__ import annotations

import os

import pytest

import calls.client as client
import calls.component as component
import pgdatabase.database as pgdatabase_database


class TestCallsContext:

    async def test_a_call_that_was_never_placed_is_not_found(self) -> None:
        config = component.Config(
            component.Spec(
                storage=os.environ["CALLS_STORAGE"],
                restate_url=os.environ["RESTATE_URL"],
                livekit_url="ws://livekit.invalid",
                livekit_api_key="unused",
                livekit_api_secret="unused",
                livekit_agent_name="caller",
            )
        )
        database = pgdatabase_database.Database(config.database)
        await database.open()
        calls = component.Calls(config, database)

        with pytest.raises(client.CallNotFound) as raised:
            await calls.client.get_call(client.GetCallRequest(call_id="ctx-never-placed"))
        await calls.close()
        await database.close()

        assert str(raised.value) == "no call 'ctx-never-placed'"
