from __future__ import annotations

import json
import typing

import tesser.application as ts

import calls.application.snapshots as snapshots
import calls.domain as domain
import tesser.errors as errors


class DialPersonRequest(ts.Request):

    def __init__(self, call: domain.Call) -> None:
        self.call = call


class DialPersonRequestSnapshot(ts.Serde):

    def serialize(self, dial_person_request: DialPersonRequest) -> bytes:
        return snapshots.CallSnapshot().serialize(dial_person_request.call)

    def deserialize(self, buf: bytes) -> DialPersonRequest:
        return DialPersonRequest(call=snapshots.CallSnapshot().deserialize(buf))


class DialPersonResponse(ts.Response):

    def __init__(self, call_id: str) -> None:
        self.call_id = call_id


class DialPersonResponseSnapshot(ts.Serde):

    def serialize(self, dial_person_response: DialPersonResponse) -> bytes:
        return json.dumps({"call_id": dial_person_response.call_id}).encode()

    def deserialize(self, buf: bytes) -> DialPersonResponse:
        snapshot = json.loads(buf)
        if not (isinstance(snapshot, dict) and isinstance(snapshot.get("call_id"), str)):
            raise errors.invalid("invalid_snapshot", "a dial person response is a call_id")
        return DialPersonResponse(call_id=snapshot["call_id"])


class DialPersonRelay(ts.Relay, typing.Protocol):

    async def run_dial_person(self, dial_person_request: DialPersonRequest) -> DialPersonResponse: ...
