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

    def __init__(self, call_id: str, text: str, person_names: tuple[str, ...]) -> None:
        self.call_id = call_id
        self.text = text
        self.person_names = person_names


class EndPersonTurnRequest(ts.Request):

    def __init__(self, call_id: str) -> None:
        self.call_id = call_id


class EndPersonTurnResponse(ts.Response):

    def __init__(self, call_id: str) -> None:
        self.call_id = call_id


class Speech(ts.Port, typing.Protocol):

    async def speak_turn(self, speak_turn_request: SpeakTurnRequest) -> SpeakTurnResponse: ...

    async def end_person_turn(self, end_person_turn_request: EndPersonTurnRequest) -> EndPersonTurnResponse: ...
