from __future__ import annotations

import json
import typing

import tesser.application as ts

import calls.application.snapshots as snapshots
import calls.domain as domain
import tesser.errors as errors


class ConductCallRequest(ts.Request):

    def __init__(self, call: domain.Call) -> None:
        self.call = call


class ConductCallRequestSnapshot(ts.Serde):

    def serialize(self, conduct_call_request: ConductCallRequest) -> bytes:
        return snapshots.CallSnapshot().serialize(conduct_call_request.call)

    def deserialize(self, buf: bytes) -> ConductCallRequest:
        return ConductCallRequest(call=snapshots.CallSnapshot().deserialize(buf))


class ConductCallResponse(ts.Response):

    def __init__(self, call_id: str) -> None:
        self.call_id = call_id


class ConductCallResponseSnapshot(ts.Serde):

    def serialize(self, conduct_call_response: ConductCallResponse) -> bytes:
        return json.dumps({"call_id": conduct_call_response.call_id}).encode()

    def deserialize(self, buf: bytes) -> ConductCallResponse:
        snapshot = json.loads(buf)
        if not (isinstance(snapshot, dict) and isinstance(snapshot.get("call_id"), str)):
            raise errors.invalid("invalid_snapshot", "a conduct call response is a call_id")
        return ConductCallResponse(call_id=snapshot["call_id"])


class ConductCallRelay(ts.Relay, typing.Protocol):

    async def run_conduct_call(self, conduct_call_request: ConductCallRequest) -> ConductCallResponse: ...
