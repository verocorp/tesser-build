from __future__ import annotations

import json
import typing

import tesser.application as ts

import tesser.errors as errors


class PlaceCallRequest(ts.Request):

    def __init__(self, call_id: str, person_name: str, phone_number: str) -> None:
        self.call_id = call_id
        self.person_name = person_name
        self.phone_number = phone_number


class PlaceCallRequestSnapshot(ts.Serde):

    def serialize(self, place_call_request: PlaceCallRequest) -> bytes:
        return json.dumps(
            {
                "call_id": place_call_request.call_id,
                "person_name": place_call_request.person_name,
                "phone_number": place_call_request.phone_number,
            }
        ).encode()

    def deserialize(self, buf: bytes) -> PlaceCallRequest:
        snapshot = json.loads(buf)
        if not (
            isinstance(snapshot, dict)
            and isinstance(snapshot.get("call_id"), str)
            and isinstance(snapshot.get("person_name"), str)
            and isinstance(snapshot.get("phone_number"), str)
        ):
            raise errors.invalid(
                "invalid_snapshot", "a place call request is a call_id, a person_name, and a phone_number"
            )
        return PlaceCallRequest(
            call_id=snapshot["call_id"],
            person_name=snapshot["person_name"],
            phone_number=snapshot["phone_number"],
        )


class PlaceCallResponse(ts.Response):

    def __init__(self, call_id: str) -> None:
        self.call_id = call_id


class PlaceCallResponseSnapshot(ts.Serde):

    def serialize(self, place_call_response: PlaceCallResponse) -> bytes:
        return json.dumps({"call_id": place_call_response.call_id}).encode()

    def deserialize(self, buf: bytes) -> PlaceCallResponse:
        snapshot = json.loads(buf)
        if not (isinstance(snapshot, dict) and isinstance(snapshot.get("call_id"), str)):
            raise errors.invalid("invalid_snapshot", "a place call response is a call_id")
        return PlaceCallResponse(call_id=snapshot["call_id"])


class CallOrchestratorRunner(ts.Relay, typing.Protocol):

    async def run_place_call(self, place_call_request: PlaceCallRequest) -> PlaceCallResponse: ...
