from __future__ import annotations

import json
import typing

import tesser.application as ts

import calls.application.snapshots as snapshots
import calls.domain as domain
import tesser.errors as errors


class SpeakTurnRequest(ts.Request):
    def __init__(self, call: domain.Call) -> None:
        self.call = call


class SpeakTurnRequestSnapshot(ts.Serde):
    def serialize(self, speak_turn_request: SpeakTurnRequest) -> bytes:
        return snapshots.CallSnapshot().serialize(speak_turn_request.call)

    def deserialize(self, buf: bytes) -> SpeakTurnRequest:
        return SpeakTurnRequest(call=snapshots.CallSnapshot().deserialize(buf))


class SpeakTurnResponse(ts.Response):
    def __init__(self, call_id: str, text: str) -> None:
        self.call_id = call_id
        self.text = text


class SpeakTurnResponseSnapshot(ts.Serde):
    def serialize(self, speak_turn_response: SpeakTurnResponse) -> bytes:
        return json.dumps(
            {
                "call_id": speak_turn_response.call_id,
                "text": speak_turn_response.text,
            }
        ).encode()

    def deserialize(self, buf: bytes) -> SpeakTurnResponse:
        snapshot = json.loads(buf)
        if not (
            isinstance(snapshot, dict)
            and isinstance(snapshot.get("call_id"), str)
            and isinstance(snapshot.get("text"), str)
        ):
            raise errors.invalid(
                "invalid_snapshot", "a speak turn response is a call_id, a text, and the person names given"
            )
        return SpeakTurnResponse(call_id=snapshot["call_id"], text=snapshot["text"])


class SpeechRelay(ts.Relay, typing.Protocol):  # tesser:debt TB085
    async def run_speak_turn(self, speak_turn_request: SpeakTurnRequest) -> SpeakTurnResponse: ...
