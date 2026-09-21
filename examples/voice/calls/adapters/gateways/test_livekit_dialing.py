from __future__ import annotations

import typing

import tesser.testing as ts
import livekit.api as livekit_api

import calls.adapters.gateways as gateways
import calls.application.ports as ports


@ts.fake
class FakeAgentDispatchService:  # tesser:debt TB072

    def __init__(self, dispatched: list[livekit_api.CreateAgentDispatchRequest]) -> None:
        self._dispatched = dispatched

    async def create_dispatch(
        self, create_agent_dispatch_request: livekit_api.CreateAgentDispatchRequest
    ) -> livekit_api.AgentDispatch:
        self._dispatched.append(create_agent_dispatch_request)
        return livekit_api.AgentDispatch(id="d1", room=create_agent_dispatch_request.room)


@ts.fake
class FakeRoomService:  # tesser:debt TB072

    def __init__(self, deleted: list[livekit_api.DeleteRoomRequest]) -> None:
        self._deleted = deleted

    async def delete_room(self, delete_room_request: livekit_api.DeleteRoomRequest) -> livekit_api.DeleteRoomResponse:
        self._deleted.append(delete_room_request)
        return livekit_api.DeleteRoomResponse()


@ts.fake
class FakeLiveKitAPI:  # tesser:debt TB072

    opened: typing.ClassVar[list[tuple[str, str, str]]] = []
    closed: typing.ClassVar[list[bool]] = []
    dispatched: typing.ClassVar[list[livekit_api.CreateAgentDispatchRequest]] = []
    deleted: typing.ClassVar[list[livekit_api.DeleteRoomRequest]] = []

    def __init__(self, url: str, api_key: str, api_secret: str) -> None:
        FakeLiveKitAPI.opened.append((url, api_key, api_secret))
        self.agent_dispatch = FakeAgentDispatchService(FakeLiveKitAPI.dispatched)
        self.room = FakeRoomService(FakeLiveKitAPI.deleted)

    async def aclose(self) -> None:
        FakeLiveKitAPI.closed.append(True)


class TestLivekitDialing:

    async def test_dialing_dispatches_the_named_agent_into_the_room_named_for_the_call(self) -> None:
        FakeLiveKitAPI.dispatched = []
        livekit_dialing = gateways.LivekitDialing(
            typing.cast(type[livekit_api.LiveKitAPI], FakeLiveKitAPI), "ws://livekit", "key", "secret", "caller"
        )

        await livekit_dialing.dial_person(ports.DialPersonRequest(call_id="c7"))

        assert [
            (create_agent_dispatch_request.agent_name, create_agent_dispatch_request.room)
            for create_agent_dispatch_request in FakeLiveKitAPI.dispatched
        ] == [("caller", "c7")]

    async def test_dialing_opens_the_api_with_the_credentials_it_was_given_and_closes_it_after(self) -> None:
        FakeLiveKitAPI.opened = []
        FakeLiveKitAPI.closed = []
        livekit_dialing = gateways.LivekitDialing(
            typing.cast(type[livekit_api.LiveKitAPI], FakeLiveKitAPI), "ws://livekit", "key", "secret", "caller"
        )

        await livekit_dialing.dial_person(ports.DialPersonRequest(call_id="c7"))

        assert FakeLiveKitAPI.opened == [("ws://livekit", "key", "secret")]
        assert FakeLiveKitAPI.closed == [True]

    async def test_dialing_answers_the_call_id_it_dialed_for(self) -> None:
        livekit_dialing = gateways.LivekitDialing(
            typing.cast(type[livekit_api.LiveKitAPI], FakeLiveKitAPI), "ws://livekit", "key", "secret", "caller"
        )

        dial_person_response = await livekit_dialing.dial_person(ports.DialPersonRequest(call_id="c7"))

        assert dial_person_response.call_id == "c7"

    async def test_hanging_up_deletes_the_room_named_for_the_call(self) -> None:
        FakeLiveKitAPI.deleted = []
        livekit_dialing = gateways.LivekitDialing(
            typing.cast(type[livekit_api.LiveKitAPI], FakeLiveKitAPI), "ws://livekit", "key", "secret", "caller"
        )

        await livekit_dialing.hang_up(ports.HangUpRequest(call_id="c7"))

        assert [delete_room_request.room for delete_room_request in FakeLiveKitAPI.deleted] == ["c7"]

    async def test_hanging_up_opens_the_api_with_the_credentials_it_was_given_and_closes_it_after(self) -> None:
        FakeLiveKitAPI.opened = []
        FakeLiveKitAPI.closed = []
        livekit_dialing = gateways.LivekitDialing(
            typing.cast(type[livekit_api.LiveKitAPI], FakeLiveKitAPI), "ws://livekit", "key", "secret", "caller"
        )

        await livekit_dialing.hang_up(ports.HangUpRequest(call_id="c7"))

        assert FakeLiveKitAPI.opened == [("ws://livekit", "key", "secret")]
        assert FakeLiveKitAPI.closed == [True]

    async def test_hanging_up_answers_the_call_id_it_hung_up(self) -> None:
        livekit_dialing = gateways.LivekitDialing(
            typing.cast(type[livekit_api.LiveKitAPI], FakeLiveKitAPI), "ws://livekit", "key", "secret", "caller"
        )

        hang_up_response = await livekit_dialing.hang_up(ports.HangUpRequest(call_id="c7"))

        assert hang_up_response.call_id == "c7"
