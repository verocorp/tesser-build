from __future__ import annotations

import json
import typing

import tesser.application as ts

import tesser.errors as errors


class PersonJoinedRequest(ts.Request):
    def __init__(self, call_id: str) -> None:
        self.call_id = call_id


class PersonJoinedRequestSnapshot(ts.Serde):
    def serialize(self, person_joined_request: PersonJoinedRequest) -> bytes:
        return json.dumps({"call_id": person_joined_request.call_id}).encode()

    def deserialize(self, buf: bytes) -> PersonJoinedRequest:
        snapshot = json.loads(buf)
        if not (isinstance(snapshot, dict) and isinstance(snapshot.get("call_id"), str)):
            raise errors.invalid("invalid_snapshot", "a person joined request is a call_id")
        return PersonJoinedRequest(call_id=snapshot["call_id"])


class PersonJoinedResponse(ts.Response):
    def __init__(self, call_id: str) -> None:
        self.call_id = call_id


class PersonJoinedResponseSnapshot(ts.Serde):
    def serialize(self, person_joined_response: PersonJoinedResponse) -> bytes:
        return json.dumps({"call_id": person_joined_response.call_id}).encode()

    def deserialize(self, buf: bytes) -> PersonJoinedResponse:
        snapshot = json.loads(buf)
        if not (isinstance(snapshot, dict) and isinstance(snapshot.get("call_id"), str)):
            raise errors.invalid("invalid_snapshot", "a person joined response is a call_id")
        return PersonJoinedResponse(call_id=snapshot["call_id"])


class PersonTurnCompletedRequest(ts.Request):
    def __init__(self, call_id: str, text: str) -> None:
        self.call_id = call_id
        self.text = text


class PersonTurnCompletedRequestSnapshot(ts.Serde):
    def serialize(self, person_turn_completed_request: PersonTurnCompletedRequest) -> bytes:
        return json.dumps(
            {"call_id": person_turn_completed_request.call_id, "text": person_turn_completed_request.text}
        ).encode()

    def deserialize(self, buf: bytes) -> PersonTurnCompletedRequest:
        snapshot = json.loads(buf)
        if not (
            isinstance(snapshot, dict)
            and isinstance(snapshot.get("call_id"), str)
            and isinstance(snapshot.get("text"), str)
        ):
            raise errors.invalid("invalid_snapshot", "a person turn completed request is a call_id and a text")
        return PersonTurnCompletedRequest(call_id=snapshot["call_id"], text=snapshot["text"])


class PersonTurnCompletedResponse(ts.Response):
    def __init__(self, call_id: str) -> None:
        self.call_id = call_id


class PersonTurnCompletedResponseSnapshot(ts.Serde):
    def serialize(self, person_turn_completed_response: PersonTurnCompletedResponse) -> bytes:
        return json.dumps({"call_id": person_turn_completed_response.call_id}).encode()

    def deserialize(self, buf: bytes) -> PersonTurnCompletedResponse:
        snapshot = json.loads(buf)
        if not (isinstance(snapshot, dict) and isinstance(snapshot.get("call_id"), str)):
            raise errors.invalid("invalid_snapshot", "a person turn completed response is a call_id")
        return PersonTurnCompletedResponse(call_id=snapshot["call_id"])


class CallEventsRelay(ts.Relay, typing.Protocol):  # tesser:debt TB085
    async def run_person_joined(self, person_joined_request: PersonJoinedRequest) -> PersonJoinedResponse: ...

    async def run_person_turn_completed(
        self, person_turn_completed_request: PersonTurnCompletedRequest
    ) -> PersonTurnCompletedResponse: ...
