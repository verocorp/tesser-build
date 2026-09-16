from __future__ import annotations

import json
import typing

import tesser.application as ts

import calls.application.snapshots as snapshots
import calls.domain as domain
import tesser.errors as errors


class HangUpRequest(ts.Request):

    def __init__(self, call: domain.Call) -> None:
        self.call = call


class HangUpRequestSnapshot(ts.Serde):

    def serialize(self, hang_up_request: HangUpRequest) -> bytes:
        return snapshots.CallSnapshot().serialize(hang_up_request.call)

    def deserialize(self, buf: bytes) -> HangUpRequest:
        return HangUpRequest(call=snapshots.CallSnapshot().deserialize(buf))


class HangUpResponse(ts.Response):

    def __init__(self, call_id: str) -> None:
        self.call_id = call_id


class HangUpResponseSnapshot(ts.Serde):

    def serialize(self, hang_up_response: HangUpResponse) -> bytes:
        return json.dumps({"call_id": hang_up_response.call_id}).encode()

    def deserialize(self, buf: bytes) -> HangUpResponse:
        snapshot = json.loads(buf)
        if not (isinstance(snapshot, dict) and isinstance(snapshot.get("call_id"), str)):
            raise errors.invalid("invalid_snapshot", "a hang up response is a call_id")
        return HangUpResponse(call_id=snapshot["call_id"])


class HangUpRelay(ts.Relay, typing.Protocol):

    async def run_hang_up(self, hang_up_request: HangUpRequest) -> HangUpResponse: ...
