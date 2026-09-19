from __future__ import annotations

import typing

import tesser.application as ts

import calls.application.relays as relays


class InterpretationApplicationClient(ts.Client, typing.Protocol):
    async def interpret_turn(
        self, interpret_turn_request: relays.InterpretTurnRequest
    ) -> relays.InterpretTurnResponse: ...
