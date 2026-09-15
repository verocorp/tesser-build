from __future__ import annotations

import json
import typing

import tesser.application as ts

import calls.application.snapshots as snapshots
import calls.domain as domain
import tesser.errors as errors


class RecordCallRequest(ts.Request):

    def __init__(self, call: domain.Call) -> None:
        self.call = call


class RecordCallRequestSnapshot(ts.Serde):

    def serialize(self, record_call_request: RecordCallRequest) -> bytes:
        return snapshots.CallSnapshot().serialize(record_call_request.call)

    def deserialize(self, buf: bytes) -> RecordCallRequest:
        return RecordCallRequest(call=snapshots.CallSnapshot().deserialize(buf))


class RecordCallResponse(ts.Response):

    def __init__(self, call_id: str) -> None:
        self.call_id = call_id


class RecordCallResponseSnapshot(ts.Serde):

    def serialize(self, record_call_response: RecordCallResponse) -> bytes:
        return json.dumps({"call_id": record_call_response.call_id}).encode()

    def deserialize(self, buf: bytes) -> RecordCallResponse:
        snapshot = json.loads(buf)
        if not (isinstance(snapshot, dict) and isinstance(snapshot.get("call_id"), str)):
            raise errors.invalid("invalid_snapshot", "a record call response is a call_id")
        return RecordCallResponse(call_id=snapshot["call_id"])


class RecordCallRelay(ts.Relay, typing.Protocol):

    async def run_record_call(self, record_call_request: RecordCallRequest) -> RecordCallResponse: ...
