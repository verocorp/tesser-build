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


class PersonInputRequest(ts.Request):
    def __init__(self, call_id: str, kind: str, text: str) -> None:
        self.call_id = call_id
        self.kind = kind
        self.text = text


class PersonInputRequestSnapshot(ts.Serde):
    def serialize(self, person_input_request: PersonInputRequest) -> bytes:
        return json.dumps(
            {
                "call_id": person_input_request.call_id,
                "kind": person_input_request.kind,
                "text": person_input_request.text,
            }
        ).encode()

    def deserialize(self, buf: bytes) -> PersonInputRequest:
        snapshot = json.loads(buf)
        if not (
            isinstance(snapshot, dict)
            and isinstance(snapshot.get("call_id"), str)
            and isinstance(snapshot.get("kind"), str)
            and isinstance(snapshot.get("text"), str)
        ):
            raise errors.invalid("invalid_snapshot", "a person utterance request is a call_id and a text")
        return PersonInputRequest(call_id=snapshot["call_id"], kind=snapshot["kind"], text=snapshot["text"])


class PersonInputResponse(ts.Response):
    def __init__(self, call_id: str) -> None:
        self.call_id = call_id


class PersonInputResponseSnapshot(ts.Serde):
    def serialize(self, person_input_response: PersonInputResponse) -> bytes:
        return json.dumps({"call_id": person_input_response.call_id}).encode()

    def deserialize(self, buf: bytes) -> PersonInputResponse:
        snapshot = json.loads(buf)
        if not (isinstance(snapshot, dict) and isinstance(snapshot.get("call_id"), str)):
            raise errors.invalid("invalid_snapshot", "a person utterance response is a call_id")
        return PersonInputResponse(call_id=snapshot["call_id"])


class CallEventsRelay(ts.Relay, typing.Protocol):  # tesser:debt TB085
    async def run_person_answered(self, person_answered_request: PersonAnsweredRequest) -> PersonAnsweredResponse: ...

    async def run_person_input(self, person_input_request: PersonInputRequest) -> PersonInputResponse: ...
