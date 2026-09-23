from __future__ import annotations

import typing

import tesser.application as ts


class SayUtteranceRequest(ts.Request):
    def __init__(self, call_id: str, text: str) -> None:
        self.call_id = call_id
        self.text = text


class SayUtteranceResponse(ts.Response):
    def __init__(self, call_id: str) -> None:
        self.call_id = call_id


class Speech(ts.Port, typing.Protocol):
    async def say_utterance(self, say_utterance_request: SayUtteranceRequest) -> SayUtteranceResponse: ...
