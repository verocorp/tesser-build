from __future__ import annotations

import enum
import typing

import tesser.application as ts


class SpokenBy(enum.Enum):
    AGENT = "agent"
    PERSON = "person"


class SpokenTurn(ts.Response):
    def __init__(self, spoken_by: SpokenBy, text: str) -> None:
        self.spoken_by = spoken_by
        self.text = text


class SpeakTurnRequest(ts.Request):
    def __init__(self, call_id: str, persona: str, turns: tuple[SpokenTurn, ...], instructions: str) -> None:
        self.call_id = call_id
        self.persona = persona
        self.turns = turns
        self.instructions = instructions


class SpeakTurnResponse(ts.Response):
    def __init__(self, call_id: str, text: str) -> None:
        self.call_id = call_id
        self.text = text


class Speech(ts.Port, typing.Protocol):
    async def speak_turn(self, speak_turn_request: SpeakTurnRequest) -> SpeakTurnResponse: ...
