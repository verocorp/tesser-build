from __future__ import annotations

import typing

import tesser.application as ts

import calls.application.relays as relays


class SpeechApplicationClient(ts.Client, typing.Protocol):
    async def say_utterance(
        self, say_utterance_request: relays.SayUtteranceRequest
    ) -> relays.SayUtteranceResponse: ...
