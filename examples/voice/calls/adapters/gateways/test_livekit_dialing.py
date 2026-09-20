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
class FakeSipService:  # tesser:debt TB072

    def __init__(self, dialed: list[livekit_api.CreateSIPParticipantRequest]) -> None:
        self._dialed = dialed

    async def create_sip_participant(
        self, create_sip_participant_request: livekit_api.CreateSIPParticipantRequest
    ) -> livekit_api.SIPParticipantInfo:
        self._dialed.append(create_sip_participant_request)
        return livekit_api.SIPParticipantInfo(
            participant_identity=create_sip_participant_request.participant_identity,
            room_name=create_sip_participant_request.room_name,
        )


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
    dialed: typing.ClassVar[list[livekit_api.CreateSIPParticipantRequest]] = []
    deleted: typing.ClassVar[list[livekit_api.DeleteRoomRequest]] = []

    def __init__(self, url: str, api_key: str, api_secret: str) -> None:
        FakeLiveKitAPI.opened.append((url, api_key, api_secret))
        self.agent_dispatch = FakeAgentDispatchService(FakeLiveKitAPI.dispatched)
        self.sip = FakeSipService(FakeLiveKitAPI.dialed)
        self.room = FakeRoomService(FakeLiveKitAPI.deleted)

    async def aclose(self) -> None:
        FakeLiveKitAPI.closed.append(True)


@ts.helper
def dial_person_request(call_id: str = "c7", phone_number: str = "+15555550100") -> ports.DialPersonRequest:
    return ports.DialPersonRequest(call_id=call_id, phone_number=phone_number)


class TestLivekitDialing:

    async def test_a_room_call_dispatches_the_agent_without_dialing_sip(self) -> None:
        FakeLiveKitAPI.dispatched = []
        FakeLiveKitAPI.dialed = []
        livekit_dialing = gateways.LivekitDialing(
            typing.cast(type[livekit_api.LiveKitAPI], FakeLiveKitAPI), "ws://livekit", "key", "secret", "caller", ""
        )

        await livekit_dialing.dial_person(dial_person_request(call_id="c7", phone_number=""))

        assert [(d.agent_name, d.room) for d in FakeLiveKitAPI.dispatched] == [("caller", "c7")]
        assert FakeLiveKitAPI.dialed == []

    async def test_dialing_dispatches_the_named_agent_into_the_room_named_for_the_call(self) -> None:
        FakeLiveKitAPI.dispatched = []
        livekit_dialing = gateways.LivekitDialing(
            typing.cast(type[livekit_api.LiveKitAPI], FakeLiveKitAPI), "ws://livekit", "key", "secret", "caller", "ST_1"
        )

        await livekit_dialing.dial_person(dial_person_request(call_id="c7"))

        assert [(d.agent_name, d.room) for d in FakeLiveKitAPI.dispatched] == [("caller", "c7")]

    async def test_dialing_places_the_sip_call_to_the_person_into_that_room_without_waiting_for_an_answer(self) -> None:
        FakeLiveKitAPI.dialed = []
        livekit_dialing = gateways.LivekitDialing(
            typing.cast(type[livekit_api.LiveKitAPI], FakeLiveKitAPI), "ws://livekit", "key", "secret", "caller", "ST_1"
        )

        await livekit_dialing.dial_person(dial_person_request(call_id="c7", phone_number="+15555550100"))

        assert [
            (d.sip_trunk_id, d.sip_call_to, d.room_name, d.participant_identity, d.wait_until_answered)
            for d in FakeLiveKitAPI.dialed
        ] == [("ST_1", "+15555550100", "c7", "person", False)]

    async def test_dialing_opens_the_api_with_the_credentials_it_was_given_and_closes_it_after(self) -> None:
        FakeLiveKitAPI.opened = []
        FakeLiveKitAPI.closed = []
        livekit_dialing = gateways.LivekitDialing(
            typing.cast(type[livekit_api.LiveKitAPI], FakeLiveKitAPI), "ws://livekit", "key", "secret", "caller", "ST_1"
        )

        await livekit_dialing.dial_person(dial_person_request())

        assert FakeLiveKitAPI.opened == [("ws://livekit", "key", "secret")]
        assert FakeLiveKitAPI.closed == [True]

    async def test_dialing_answers_the_call_id_it_dialed_for(self) -> None:
        livekit_dialing = gateways.LivekitDialing(
            typing.cast(type[livekit_api.LiveKitAPI], FakeLiveKitAPI), "ws://livekit", "key", "secret", "caller", "ST_1"
        )

        dial_person_response = await livekit_dialing.dial_person(dial_person_request(call_id="c7"))

        assert dial_person_response.call_id == "c7"

    async def test_hanging_up_deletes_the_room_named_for_the_call(self) -> None:
        FakeLiveKitAPI.deleted = []
        livekit_dialing = gateways.LivekitDialing(
            typing.cast(type[livekit_api.LiveKitAPI], FakeLiveKitAPI), "ws://livekit", "key", "secret", "caller", "ST_1"
        )

        await livekit_dialing.hang_up(ports.HangUpRequest(call_id="c7"))

        assert [d.room for d in FakeLiveKitAPI.deleted] == ["c7"]
