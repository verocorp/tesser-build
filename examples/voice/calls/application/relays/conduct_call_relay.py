from __future__ import annotations

import json
import typing

import tesser.application as ts

import tesser.errors as errors


class ConductCallRequest(ts.Request):

    def __init__(self, call_id: str, person_name: str, phone_number: str) -> None:
        self.call_id = call_id
        self.person_name = person_name
        self.phone_number = phone_number


class ConductCallRequestSnapshot(ts.Serde):

    def serialize(self, conduct_call_request: ConductCallRequest) -> bytes:
        return json.dumps(
            {
                "call_id": conduct_call_request.call_id,
                "person_name": conduct_call_request.person_name,
                "phone_number": conduct_call_request.phone_number,
            }
        ).encode()

    def deserialize(self, buf: bytes) -> ConductCallRequest:
        snapshot = json.loads(buf)
        if not (
            isinstance(snapshot, dict)
            and isinstance(snapshot.get("call_id"), str)
            and isinstance(snapshot.get("person_name"), str)
            and isinstance(snapshot.get("phone_number"), str)
        ):
            raise errors.invalid(
                "invalid_snapshot", "a conduct call request is a call_id, a person_name, and a phone_number"
            )
        return ConductCallRequest(
            call_id=snapshot["call_id"],
            person_name=snapshot["person_name"],
            phone_number=snapshot["phone_number"],
        )


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
