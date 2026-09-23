from __future__ import annotations

import tesser.application as ts

import calls.application.ports as ports
import calls.application.relays as relays


class MapToSayUtteranceRequest(ts.Mapper, ports.SayUtteranceRequest):
    def __init__(self, say_utterance_request: relays.SayUtteranceRequest) -> None:
        super().__init__(call_id=say_utterance_request.call_id, text=say_utterance_request.text)


class MapToSayUtteranceResponse(ts.Mapper, relays.SayUtteranceResponse):
    def __init__(self, say_utterance_response: ports.SayUtteranceResponse) -> None:
        super().__init__(call_id=say_utterance_response.call_id)


class SpeechActions(ts.Actions):
    def __init__(self, speech: ports.Speech) -> None:
        self._speech = speech

    async def say_utterance(
        self, say_utterance_request: relays.SayUtteranceRequest
    ) -> relays.SayUtteranceResponse:
        say_utterance_response = await self._speech.say_utterance(MapToSayUtteranceRequest(say_utterance_request))
        return MapToSayUtteranceResponse(say_utterance_response)
