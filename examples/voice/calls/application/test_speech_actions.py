from __future__ import annotations

import tesser.testing as ts

import calls.application as application
import calls.application.ports as ports
import calls.application.relays as relays


@ts.fake
class FakeSpeech(ports.Speech):
    def __init__(self) -> None:
        self.said: list[ports.SayUtteranceRequest] = []

    async def say_utterance(self, say_utterance_request: ports.SayUtteranceRequest) -> ports.SayUtteranceResponse:
        self.said.append(say_utterance_request)
        return ports.SayUtteranceResponse(call_id=say_utterance_request.call_id)


class TestSpeechActions:
    async def test_saying_an_utterance_hands_the_port_the_text_under_the_call_id(self) -> None:
        fake_speech = FakeSpeech()
        speech_actions = application.SpeechActions(fake_speech)

        await speech_actions.say_utterance(
            relays.SayUtteranceRequest(call_id="c7", text="Nice to meet you, Grace. Goodbye.")
        )

        assert [(said.call_id, said.text) for said in fake_speech.said] == [
            ("c7", "Nice to meet you, Grace. Goodbye.")
        ]

    async def test_saying_an_utterance_answers_the_call_id_it_spoke_on(self) -> None:
        speech_actions = application.SpeechActions(FakeSpeech())

        say_utterance_response = await speech_actions.say_utterance(
            relays.SayUtteranceRequest(call_id="c7", text="Hello. Please tell me your first name.")
        )

        assert say_utterance_response.call_id == "c7"
