from __future__ import annotations

import json
import typing

import tesser.application as ts

import tesser.errors as errors


class AwaitPersonAnsweredRequest(ts.Request):

    def __init__(self, call_id: str) -> None:
        self.call_id = call_id


class AwaitPersonAnsweredRequestSnapshot(ts.Serde):

    def serialize(self, await_person_answered_request: AwaitPersonAnsweredRequest) -> bytes:
        return json.dumps({"call_id": await_person_answered_request.call_id}).encode()

    def deserialize(self, buf: bytes) -> AwaitPersonAnsweredRequest:
        snapshot = json.loads(buf)
        if not (isinstance(snapshot, dict) and isinstance(snapshot.get("call_id"), str)):
            raise errors.invalid("invalid_snapshot", "an await person answered request is a call_id")
        return AwaitPersonAnsweredRequest(call_id=snapshot["call_id"])


class AwaitPersonAnsweredResponse(ts.Response):

    def __init__(self, call_id: str) -> None:
        self.call_id = call_id


class AwaitPersonAnsweredResponseSnapshot(ts.Serde):

    def serialize(self, await_person_answered_response: AwaitPersonAnsweredResponse) -> bytes:
        return json.dumps({"call_id": await_person_answered_response.call_id}).encode()

    def deserialize(self, buf: bytes) -> AwaitPersonAnsweredResponse:
        snapshot = json.loads(buf)
        if not (isinstance(snapshot, dict) and isinstance(snapshot.get("call_id"), str)):
            raise errors.invalid("invalid_snapshot", "an await person answered response is a call_id")
        return AwaitPersonAnsweredResponse(call_id=snapshot["call_id"])


class AwaitPersonAnsweredRelay(ts.Relay, typing.Protocol):

    async def await_person_answered(  # tesser:debt TB085
        self, await_person_answered_request: AwaitPersonAnsweredRequest
    ) -> AwaitPersonAnsweredResponse: ...
