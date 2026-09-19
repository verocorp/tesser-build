from __future__ import annotations

import tesser.application as ts

import calls.application.ports as ports
import calls.application.relays as relays
import calls.domain as domain


class MapToSpokenTurn(ts.Mapper, ports.SpokenTurn):
    def __init__(self, turn: domain.Turn) -> None:
        super().__init__(spoken_by=ports.SpokenBy(str(turn.speaker)), text=" ".join(str(u) for u in turn.utterances))


class MapToSpeakTurnRequest(ts.Mapper, ports.SpeakTurnRequest):
    def __init__(self, speak_turn_request: relays.SpeakTurnRequest) -> None:
        call = speak_turn_request.call
        super().__init__(
            call_id=str(call.identity),
            persona=str(call.persona),
            turns=tuple(MapToSpokenTurn(turn) for turn in call.conversation.turns),
            instructions=str(call.instructions),
        )


class MapToSpeakTurnResponse(ts.Mapper, relays.SpeakTurnResponse):
    def __init__(self, speak_turn_response: ports.SpeakTurnResponse) -> None:
        super().__init__(
            call_id=speak_turn_response.call_id,
            text=speak_turn_response.text,
        )


class SpeechActions(ts.Actions):
    def __init__(self, speech: ports.Speech) -> None:
        self._speech = speech

    async def speak_turn(self, speak_turn_request: relays.SpeakTurnRequest) -> relays.SpeakTurnResponse:
        speak_turn_response = await self._speech.speak_turn(MapToSpeakTurnRequest(speak_turn_request))
        return MapToSpeakTurnResponse(speak_turn_response)
