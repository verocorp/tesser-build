from __future__ import annotations

import json
import typing

import tesser.application as ts

import calls.application.snapshots as snapshots
import calls.domain as domain
import tesser.errors as errors


class EndPersonTurnRequest(ts.Request):

    def __init__(self, call: domain.Call) -> None:
        self.call = call


class EndPersonTurnRequestSnapshot(ts.Serde):

    def serialize(self, end_person_turn_request: EndPersonTurnRequest) -> bytes:
        return snapshots.CallSnapshot().serialize(end_person_turn_request.call)

    def deserialize(self, buf: bytes) -> EndPersonTurnRequest:
        return EndPersonTurnRequest(call=snapshots.CallSnapshot().deserialize(buf))


class EndPersonTurnResponse(ts.Response):

    def __init__(self, call_id: str) -> None:
        self.call_id = call_id


class EndPersonTurnResponseSnapshot(ts.Serde):

    def serialize(self, end_person_turn_response: EndPersonTurnResponse) -> bytes:
        return json.dumps({"call_id": end_person_turn_response.call_id}).encode()

    def deserialize(self, buf: bytes) -> EndPersonTurnResponse:
        snapshot = json.loads(buf)
        if not (isinstance(snapshot, dict) and isinstance(snapshot.get("call_id"), str)):
            raise errors.invalid("invalid_snapshot", "an end person turn response is a call_id")
        return EndPersonTurnResponse(call_id=snapshot["call_id"])


class EndPersonTurnRelay(ts.Relay, typing.Protocol):

    async def run_end_person_turn(self, end_person_turn_request: EndPersonTurnRequest) -> EndPersonTurnResponse: ...
