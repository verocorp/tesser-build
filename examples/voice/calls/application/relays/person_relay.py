from __future__ import annotations

import json
import typing

import tesser.application as ts

import tesser.errors as errors

INPUT_TURN_COMPLETED: typing.Final[str] = "turn_completed"
INPUT_SPEECH_STARTED: typing.Final[str] = "speech_started"
INPUT_NO_RESPONSE: typing.Final[str] = "no_response"


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


class AwaitPersonInputRequest(ts.Request):
    def __init__(self, call_id: str, within_seconds: int | None) -> None:  # tesser:debt TB080
        self.call_id = call_id
        self.within_seconds = within_seconds


class AwaitPersonInputRequestSnapshot(ts.Serde):
    def serialize(self, await_person_input_request: AwaitPersonInputRequest) -> bytes:
        return json.dumps(
            {
                "call_id": await_person_input_request.call_id,
                "within_seconds": await_person_input_request.within_seconds,
            }
        ).encode()

    def deserialize(self, buf: bytes) -> AwaitPersonInputRequest:
        snapshot = json.loads(buf)
        if not (
            isinstance(snapshot, dict)
            and isinstance(snapshot.get("call_id"), str)
            and "within_seconds" in snapshot  # tesser:debt TB082
            and (
                snapshot["within_seconds"] is None
                or (type(snapshot["within_seconds"]) is int and snapshot["within_seconds"] > 0)  # tesser:debt TB082
            )
        ):
            raise errors.invalid(
                "invalid_snapshot", "an await person utterance request is a call_id and the seconds it waits within"
            )
        return AwaitPersonInputRequest(call_id=snapshot["call_id"], within_seconds=snapshot["within_seconds"])


class AwaitPersonInputResponse(ts.Response):
    def __init__(self, call_id: str, kind: str, text: str) -> None:
        self.call_id = call_id
        self.kind = kind
        self.text = text


class AwaitPersonInputResponseSnapshot(ts.Serde):
    def serialize(self, await_person_input_response: AwaitPersonInputResponse) -> bytes:
        return json.dumps(
            {
                "call_id": await_person_input_response.call_id,
                "kind": await_person_input_response.kind,
                "text": await_person_input_response.text,
            }
        ).encode()

    def deserialize(self, buf: bytes) -> AwaitPersonInputResponse:
        snapshot = json.loads(buf)
        if not (
            isinstance(snapshot, dict)
            and isinstance(snapshot.get("call_id"), str)
            and isinstance(snapshot.get("kind"), str)
            and isinstance(snapshot.get("text"), str)
        ):
            raise errors.invalid(
                "invalid_snapshot", "an await person utterance response is a call_id, what was heard, and a text"
            )
        return AwaitPersonInputResponse(call_id=snapshot["call_id"], kind=snapshot["kind"], text=snapshot["text"])


class PersonRelay(ts.Relay, typing.Protocol):
    async def await_person_answered(  # tesser:debt TB085
        self, await_person_answered_request: AwaitPersonAnsweredRequest
    ) -> AwaitPersonAnsweredResponse: ...

    async def await_person_input(  # tesser:debt TB085
        self, await_person_input_request: AwaitPersonInputRequest
    ) -> AwaitPersonInputResponse: ...
