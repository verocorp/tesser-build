from __future__ import annotations

import json
import typing

import tesser.application as ts

import tesser.errors as errors


class RecordCallRequest(ts.Request):

    def __init__(self, call_id: str, person_name: str, phone_number: str) -> None:
        self.call_id = call_id
        self.person_name = person_name
        self.phone_number = phone_number


class RecordCallRequestSnapshot(ts.Serde):

    def serialize(self, record_call_request: RecordCallRequest) -> bytes:
        return json.dumps(
            {
                "call_id": record_call_request.call_id,
                "person_name": record_call_request.person_name,
                "phone_number": record_call_request.phone_number,
            }
        ).encode()

    def deserialize(self, buf: bytes) -> RecordCallRequest:
        snapshot = json.loads(buf)
        if not (
            isinstance(snapshot, dict)
            and isinstance(snapshot.get("call_id"), str)
            and isinstance(snapshot.get("person_name"), str)
            and isinstance(snapshot.get("phone_number"), str)
        ):
            raise errors.invalid(
                "invalid_snapshot", "a record call request is a call_id, a person_name, and a phone_number"
            )
        return RecordCallRequest(
            call_id=snapshot["call_id"],
            person_name=snapshot["person_name"],
            phone_number=snapshot["phone_number"],
        )


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
