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

    def __init__(self) -> None:
        self.dispatched: list[livekit_api.CreateAgentDispatchRequest] = []
        self.dialed: list[livekit_api.CreateSIPParticipantRequest] = []
        self.deleted: list[livekit_api.DeleteRoomRequest] = []
        self.agent_dispatch = FakeAgentDispatchService(self.dispatched)
        self.sip = FakeSipService(self.dialed)
        self.room = FakeRoomService(self.deleted)


class TestLivekitDialing:

    async def test_dialing_dispatches_the_named_agent_into_the_room_named_for_the_call(self) -> None:
        fake_livekit_api = FakeLiveKitAPI()  # tesser:debt TB085
        livekit_dialing = gateways.LivekitDialing(typing.cast(livekit_api.LiveKitAPI, fake_livekit_api), "caller", "ST_1")

        await livekit_dialing.dial_person(ports.DialPersonRequest(call_id="c7", phone_number="+15555550100"))

        assert [(d.agent_name, d.room) for d in fake_livekit_api.dispatched] == [("caller", "c7")]

    async def test_dialing_places_the_sip_call_to_the_person_into_that_room_without_waiting_for_an_answer(self) -> None:
        fake_livekit_api = FakeLiveKitAPI()  # tesser:debt TB085
        livekit_dialing = gateways.LivekitDialing(typing.cast(livekit_api.LiveKitAPI, fake_livekit_api), "caller", "ST_1")

        await livekit_dialing.dial_person(ports.DialPersonRequest(call_id="c7", phone_number="+15555550100"))

        assert [
            (d.sip_trunk_id, d.sip_call_to, d.room_name, d.participant_identity, d.wait_until_answered)
            for d in fake_livekit_api.dialed
        ] == [("ST_1", "+15555550100", "c7", "person", False)]

    async def test_dialing_answers_the_call_id_it_dialed_for(self) -> None:
        livekit_dialing = gateways.LivekitDialing(typing.cast(livekit_api.LiveKitAPI, FakeLiveKitAPI()), "caller", "ST_1")

        dial_person_response = await livekit_dialing.dial_person(
            ports.DialPersonRequest(call_id="c7", phone_number="+15555550100")
        )

        assert dial_person_response.call_id == "c7"

    async def test_hanging_up_deletes_the_room_named_for_the_call(self) -> None:
        fake_livekit_api = FakeLiveKitAPI()  # tesser:debt TB085
        livekit_dialing = gateways.LivekitDialing(typing.cast(livekit_api.LiveKitAPI, fake_livekit_api), "caller", "ST_1")

        await livekit_dialing.hang_up(ports.HangUpRequest(call_id="c7"))

        assert [d.room for d in fake_livekit_api.deleted] == ["c7"]
