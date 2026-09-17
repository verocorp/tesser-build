from __future__ import annotations

import os
import random

import pytest

import tesser.testing as ts

import app as app
import calls.client as calls_client


@ts.helper
def place_call_request(person_name: str = "Ada", phone_number: str = "+15555550100") -> calls_client.PlaceCallRequest:
    return calls_client.PlaceCallRequest(person_name=person_name, phone_number=phone_number)


class TestPlacingCalls:

    async def test_a_call_is_successfully_made(self) -> None:
        if os.environ.get("VOICE_LIVE_CALLS") != "1":
            pytest.skip("a live call needs LiveKit, a SIP trunk, and a person to answer: set VOICE_LIVE_CALLS=1")
        voice_app = app.load()
        await voice_app.open()
        person_name = random.choice(("Ada", "Grace", "Alan", "Barbara"))

        place_call_response = await voice_app.calls.client.place_call(
            place_call_request(person_name=person_name, phone_number=os.environ["VOICE_PERSON_PHONE"])
        )
        get_call_response = await voice_app.calls.client.get_call(
            calls_client.GetCallRequest(call_id=place_call_response.call_id)
        )
        await voice_app.close()

        assert get_call_response.call.person_name == person_name
