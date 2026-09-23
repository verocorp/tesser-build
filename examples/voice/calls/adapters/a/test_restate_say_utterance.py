from __future__ import annotations

import typing

import tesser.testing as ts
import restate

import calls.adapters.a as a
import calls.application.client as client
import calls.application.relays as relays


@ts.fake
class FakeSpeechApplicationClient(client.SpeechApplicationClient):
    def __init__(self) -> None:
        self.said: list[relays.SayUtteranceRequest] = []

    async def say_utterance(
        self, say_utterance_request: relays.SayUtteranceRequest
    ) -> relays.SayUtteranceResponse:
        self.said.append(say_utterance_request)
        return relays.SayUtteranceResponse(call_id=say_utterance_request.call_id)


class TestRestateSayUtterance:
    def test_it_registers_its_handler_under_the_operation_on_the_service_it_is_handed(self) -> None:
        speech_actions_service = restate.Service("SpeechActions")

        a.RestateSayUtterance(speech_actions_service, FakeSpeechApplicationClient())

        assert sorted(speech_actions_service.handlers) == ["say_utterance"]

    async def test_the_handler_hands_the_request_to_the_application_client(self) -> None:
        fake_speech_application_client = FakeSpeechApplicationClient()
        say_utterance_request = relays.SayUtteranceRequest(call_id="c7", text="Hello.")

        await a.RestateSayUtterance(restate.Service("SpeechActions"), fake_speech_application_client).handler(
            typing.cast(restate.Context, None), say_utterance_request
        )

        assert fake_speech_application_client.said == [say_utterance_request]

