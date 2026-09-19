from __future__ import annotations

import typing

import tesser.application as ts


class InterpretedConversationTurn(ts.Request):
    def __init__(self, spoken_by: str, text: str) -> None:
        self.spoken_by = spoken_by
        self.text = text


class InterpretTurnRequest(ts.Request):
    def __init__(self, call_id: str, instructions: str, turns: tuple[InterpretedConversationTurn, ...]) -> None:
        self.call_id = call_id
        self.instructions = instructions
        self.turns = turns


class InterpretTurnResponse(ts.Response):
    def __init__(self, call_id: str, person_names: tuple[str, ...]) -> None:
        self.call_id = call_id
        self.person_names = person_names


class Interpretation(ts.Port, typing.Protocol):
    async def interpret_turn(self, interpret_turn_request: InterpretTurnRequest) -> InterpretTurnResponse: ...
