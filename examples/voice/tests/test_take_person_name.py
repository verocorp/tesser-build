from __future__ import annotations

import random

import app as app
import calling.client as calling_client


class TestTakePersonName:

    async def test_a_call_holds_the_person_who_gave_their_name_on_it(self) -> None:
        voice_app = app.load()
        person = calling_client.Person(name=random.choice(("Ada", "Grace", "Alan", "Barbara")))

        place_call_response = await voice_app.calling.client.place_call(calling_client.PlaceCallRequest(person=person))
        get_call_response = await voice_app.calling.client.get_call(
            calling_client.GetCallRequest(call_id=place_call_response.call_id)
        )
        voice_app.close()

        assert get_call_response.call.person == person
