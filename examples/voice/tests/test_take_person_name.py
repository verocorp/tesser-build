from __future__ import annotations

import os
import random
import uuid

import livekit.agents.voice as livekit_voice
import livekit.agents.voice.remote_session as livekit_remote_session
import livekit.api as livekit_api
import livekit.rtc as livekit_rtc

import app as app
import calling.client as calling_client


class TestTakePersonName:

    async def test_a_person_who_says_their_name_hears_the_agent_say_it_back(self) -> None:
        person = calling_client.Person(name=random.choice(("Ada", "Grace", "Alan", "Barbara")))
        voice_app = app.load()
        place_call_response = await voice_app.calling.client.place_call(
            calling_client.PlaceCallRequest(call_id=str(uuid.uuid4()))
        )
        access_token = livekit_api.AccessToken(os.environ["LIVEKIT_API_KEY"], os.environ["LIVEKIT_API_SECRET"])
        video_grants = livekit_api.VideoGrants(room_join=True, room=place_call_response.call_id)
        room = livekit_rtc.Room()
        await room.connect(
            os.environ["LIVEKIT_URL"], access_token.with_identity("person").with_grants(video_grants).to_jwt()
        )
        remote_session = livekit_voice.RemoteSession(livekit_remote_session.RoomSessionTransport(room))
        await remote_session.start()
        await remote_session.wait_for_ready(timeout=30.0)

        run_input_response = await remote_session.run(f"my name is {person.name}")
        await remote_session.aclose()
        await room.disconnect()
        voice_app.close()

        assert person.name in run_input_response.items[-1].message.content[0].text

    async def test_a_call_where_the_person_said_their_name_holds_that_person(self) -> None:
        person = calling_client.Person(name=random.choice(("Ada", "Grace", "Alan", "Barbara")))
        voice_app = app.load()
        place_call_response = await voice_app.calling.client.place_call(
            calling_client.PlaceCallRequest(call_id=str(uuid.uuid4()))
        )
        access_token = livekit_api.AccessToken(os.environ["LIVEKIT_API_KEY"], os.environ["LIVEKIT_API_SECRET"])
        video_grants = livekit_api.VideoGrants(room_join=True, room=place_call_response.call_id)
        room = livekit_rtc.Room()
        await room.connect(
            os.environ["LIVEKIT_URL"], access_token.with_identity("person").with_grants(video_grants).to_jwt()
        )
        remote_session = livekit_voice.RemoteSession(livekit_remote_session.RoomSessionTransport(room))
        await remote_session.start()
        await remote_session.wait_for_ready(timeout=30.0)
        await remote_session.run(f"my name is {person.name}")
        await remote_session.aclose()
        await room.disconnect()

        get_call_response = await voice_app.calling.client.get_call(
            calling_client.GetCallRequest(call_id=place_call_response.call_id)
        )
        voice_app.close()

        assert get_call_response.call.person == person
