from __future__ import annotations

import random

import tesser.testing as ts

import app as app
import calls.client as calls_client


@ts.helper
def place_call_request(person_name: str = "Ada", phone_number: str = "+15555550100") -> calls_client.PlaceCallRequest:
    return calls_client.PlaceCallRequest(person_name=person_name, phone_number=phone_number)


class TestPlacingCalls:

    async def test_a_call_is_successfully_made(self) -> None:
        voice_app = app.load()
        person_name = random.choice(("Ada", "Grace", "Alan", "Barbara"))

        place_call_response = await voice_app.calls.client.place_call(place_call_request(person_name=person_name))
        get_call_response = await voice_app.calls.client.get_call(
            calls_client.GetCallRequest(call_id=place_call_response.call_id)
        )
        voice_app.close()

        assert get_call_response.call.person_name == person_name
