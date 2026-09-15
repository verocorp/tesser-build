from __future__ import annotations

import typing

import tesser.application as ts

import calls.application.relays as relays


class SpeechApplicationClient(ts.Client, typing.Protocol):

    async def speak_turn(self, speak_turn_request: relays.SpeakTurnRequest) -> relays.SpeakTurnResponse: ...
