from __future__ import annotations

import json
import typing

import tesser.application as ts

import tesser.errors as errors


class PersonAnsweredRequest(ts.Request):

    def __init__(self, call_id: str) -> None:
        self.call_id = call_id


class PersonAnsweredRequestSnapshot(ts.Serde):

    def serialize(self, person_answered_request: PersonAnsweredRequest) -> bytes:
        return json.dumps({"call_id": person_answered_request.call_id}).encode()

    def deserialize(self, buf: bytes) -> PersonAnsweredRequest:
        snapshot = json.loads(buf)
        if not (isinstance(snapshot, dict) and isinstance(snapshot.get("call_id"), str)):
            raise errors.invalid("invalid_snapshot", "a person answered request is a call_id")
        return PersonAnsweredRequest(call_id=snapshot["call_id"])


class PersonAnsweredResponse(ts.Response):

    def __init__(self, call_id: str) -> None:
        self.call_id = call_id


class PersonAnsweredResponseSnapshot(ts.Serde):

    def serialize(self, person_answered_response: PersonAnsweredResponse) -> bytes:
        return json.dumps({"call_id": person_answered_response.call_id}).encode()

    def deserialize(self, buf: bytes) -> PersonAnsweredResponse:
        snapshot = json.loads(buf)
        if not (isinstance(snapshot, dict) and isinstance(snapshot.get("call_id"), str)):
            raise errors.invalid("invalid_snapshot", "a person answered response is a call_id")
        return PersonAnsweredResponse(call_id=snapshot["call_id"])


class PersonAnsweredRelay(ts.Relay, typing.Protocol):

    async def run_person_answered(
        self, person_answered_request: PersonAnsweredRequest
    ) -> PersonAnsweredResponse: ...
