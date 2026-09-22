from __future__ import annotations

import json
import typing

import tesser.application as ts

import tesser.errors as errors


class SayUtteranceRequest(ts.Request):
    def __init__(self, call_id: str, text: str) -> None:
        self.call_id = call_id
        self.text = text


class SayUtteranceRequestSnapshot(ts.Serde):
    def serialize(self, say_utterance_request: SayUtteranceRequest) -> bytes:
        return json.dumps({"call_id": say_utterance_request.call_id, "text": say_utterance_request.text}).encode()

    def deserialize(self, buf: bytes) -> SayUtteranceRequest:
        snapshot = json.loads(buf)
        if not (
            isinstance(snapshot, dict)
            and isinstance(snapshot.get("call_id"), str)
            and isinstance(snapshot.get("text"), str)
        ):
            raise errors.invalid("invalid_snapshot", "a say utterance request is a call_id and a text")
        return SayUtteranceRequest(call_id=snapshot["call_id"], text=snapshot["text"])


class SayUtteranceResponse(ts.Response):
    def __init__(self, call_id: str) -> None:
        self.call_id = call_id


class SayUtteranceResponseSnapshot(ts.Serde):
    def serialize(self, say_utterance_response: SayUtteranceResponse) -> bytes:
        return json.dumps({"call_id": say_utterance_response.call_id}).encode()

    def deserialize(self, buf: bytes) -> SayUtteranceResponse:
        snapshot = json.loads(buf)
        if not (isinstance(snapshot, dict) and isinstance(snapshot.get("call_id"), str)):
            raise errors.invalid("invalid_snapshot", "a say utterance response is a call_id")
        return SayUtteranceResponse(call_id=snapshot["call_id"])


class SpeechActionsRelay(ts.Relay, typing.Protocol):
    async def run_say_utterance(self, say_utterance_request: SayUtteranceRequest) -> SayUtteranceResponse: ...
