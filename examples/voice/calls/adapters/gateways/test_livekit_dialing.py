from __future__ import annotations

import gc
import os
import uuid
import warnings

import pytest
import livekit.api as livekit_api

import calls.adapters.gateways as gateways
import calls.application.ports as ports


class TestLivekitDialing:

    async def test_dialing_dispatches_the_named_agent_into_the_room_named_for_the_call(self) -> None:
        call_id = f"dial-{uuid.uuid4()}"
        agent_name = f"transport-{call_id}"
        url, key, secret = os.environ["LIVEKIT_URL"], os.environ["LIVEKIT_API_KEY"], os.environ["LIVEKIT_API_SECRET"]
        livekit_dialing = gateways.LivekitDialing(url, key, secret, agent_name)
        async with livekit_api.LiveKitAPI(url, key, secret) as livekit:
            try:
                await livekit_dialing.dial_person(ports.DialPersonRequest(call_id=call_id))
                dispatched = await livekit.agent_dispatch.list_dispatch(call_id)
                assert [(dispatch.agent_name, dispatch.room) for dispatch in dispatched if dispatch.agent_name] == [
                    (agent_name, call_id)
                ]
            finally:
                await livekit.room.delete_room(livekit_api.DeleteRoomRequest(room=call_id))

    async def test_dialing_opens_the_api_with_the_credentials_it_was_given_and_closes_it_after(self) -> None:
        call_id = f"dial-{uuid.uuid4()}"
        agent_name = f"transport-{call_id}"
        url, key, secret = os.environ["LIVEKIT_URL"], os.environ["LIVEKIT_API_KEY"], os.environ["LIVEKIT_API_SECRET"]
        async with livekit_api.LiveKitAPI(url, key, secret) as livekit:
            try:
                with warnings.catch_warnings(record=True) as recorded:
                    warnings.simplefilter("always", ResourceWarning)
                    await gateways.LivekitDialing(url, key, secret, agent_name).dial_person(
                        ports.DialPersonRequest(call_id=call_id)
                    )
                    gc.collect()
                assert not [warning for warning in recorded if issubclass(warning.category, ResourceWarning)]
                rooms = await livekit.room.list_rooms(livekit_api.ListRoomsRequest(names=[call_id]))
                assert [room.name for room in rooms.rooms] == [call_id]
                with pytest.raises(livekit_api.TwirpError) as raised:
                    await gateways.LivekitDialing(url, key, "invalid-secret", agent_name).dial_person(
                        ports.DialPersonRequest(call_id=call_id)
                    )
                assert raised.value.status == 401
            finally:
                await livekit.room.delete_room(livekit_api.DeleteRoomRequest(room=call_id))

    async def test_dialing_answers_the_call_id_it_dialed_for(self) -> None:
        call_id = f"dial-{uuid.uuid4()}"
        agent_name = f"transport-{call_id}"
        url, key, secret = os.environ["LIVEKIT_URL"], os.environ["LIVEKIT_API_KEY"], os.environ["LIVEKIT_API_SECRET"]
        async with livekit_api.LiveKitAPI(url, key, secret) as livekit:
            try:
                dial_person_response = await gateways.LivekitDialing(url, key, secret, agent_name).dial_person(
                    ports.DialPersonRequest(call_id=call_id)
                )
                assert dial_person_response.call_id == call_id
            finally:
                await livekit.room.delete_room(livekit_api.DeleteRoomRequest(room=call_id))

    async def test_hanging_up_deletes_the_room_named_for_the_call(self) -> None:
        call_id = f"hangup-{uuid.uuid4()}"
        agent_name = f"transport-{call_id}"
        url, key, secret = os.environ["LIVEKIT_URL"], os.environ["LIVEKIT_API_KEY"], os.environ["LIVEKIT_API_SECRET"]
        async with livekit_api.LiveKitAPI(url, key, secret) as livekit:
            await livekit.room.create_room(livekit_api.CreateRoomRequest(name=call_id))
            await gateways.LivekitDialing(url, key, secret, agent_name).hang_up(ports.HangUpRequest(call_id=call_id))
            rooms = await livekit.room.list_rooms(livekit_api.ListRoomsRequest(names=[call_id]))
            assert rooms.rooms == []

    async def test_hanging_up_opens_the_api_with_the_credentials_it_was_given_and_closes_it_after(self) -> None:
        call_id = f"hangup-{uuid.uuid4()}"
        agent_name = f"transport-{call_id}"
        url, key, secret = os.environ["LIVEKIT_URL"], os.environ["LIVEKIT_API_KEY"], os.environ["LIVEKIT_API_SECRET"]
        async with livekit_api.LiveKitAPI(url, key, secret) as livekit:
            await livekit.room.create_room(livekit_api.CreateRoomRequest(name=call_id))
            with pytest.raises(livekit_api.TwirpError) as raised:
                await gateways.LivekitDialing(url, key, "invalid-secret", agent_name).hang_up(
                    ports.HangUpRequest(call_id=call_id)
                )
            assert raised.value.status == 401
            with warnings.catch_warnings(record=True) as recorded:
                warnings.simplefilter("always", ResourceWarning)
                await gateways.LivekitDialing(url, key, secret, agent_name).hang_up(ports.HangUpRequest(call_id=call_id))
                gc.collect()
            assert not [warning for warning in recorded if issubclass(warning.category, ResourceWarning)]
            rooms = await livekit.room.list_rooms(livekit_api.ListRoomsRequest(names=[call_id]))
            assert rooms.rooms == []

    async def test_hanging_up_answers_the_call_id_it_hung_up(self) -> None:
        call_id = f"hangup-{uuid.uuid4()}"
        agent_name = f"transport-{call_id}"
        url, key, secret = os.environ["LIVEKIT_URL"], os.environ["LIVEKIT_API_KEY"], os.environ["LIVEKIT_API_SECRET"]
        async with livekit_api.LiveKitAPI(url, key, secret) as livekit:
            await livekit.room.create_room(livekit_api.CreateRoomRequest(name=call_id))
            hang_up_response = await gateways.LivekitDialing(url, key, secret, agent_name).hang_up(
                ports.HangUpRequest(call_id=call_id)
            )
            assert hang_up_response.call_id == call_id
