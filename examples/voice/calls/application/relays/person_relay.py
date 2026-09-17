from __future__ import annotations

import json
import typing

import tesser.application as ts

import tesser.errors as errors

HEARD_UTTERANCE: typing.Final[str] = "utterance"
HEARD_SILENCE: typing.Final[str] = "silence"


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


class AwaitPersonUtteranceRequest(ts.Request):

    def __init__(self, call_id: str, within_seconds: int) -> None:
        self.call_id = call_id
        self.within_seconds = within_seconds


class AwaitPersonUtteranceRequestSnapshot(ts.Serde):

    def serialize(self, await_person_utterance_request: AwaitPersonUtteranceRequest) -> bytes:
        return json.dumps(
            {
                "call_id": await_person_utterance_request.call_id,
                "within_seconds": await_person_utterance_request.within_seconds,
            }
        ).encode()

    def deserialize(self, buf: bytes) -> AwaitPersonUtteranceRequest:
        snapshot = json.loads(buf)
        if not (
            isinstance(snapshot, dict)
            and isinstance(snapshot.get("call_id"), str)
            and isinstance(snapshot.get("within_seconds"), int)
        ):
            raise errors.invalid(
                "invalid_snapshot", "an await person utterance request is a call_id and the seconds it waits within"
            )
        return AwaitPersonUtteranceRequest(call_id=snapshot["call_id"], within_seconds=snapshot["within_seconds"])


class AwaitPersonUtteranceResponse(ts.Response):

    def __init__(self, call_id: str, heard: str, text: str) -> None:
        self.call_id = call_id
        self.heard = heard
        self.text = text


class AwaitPersonUtteranceResponseSnapshot(ts.Serde):

    def serialize(self, await_person_utterance_response: AwaitPersonUtteranceResponse) -> bytes:
        return json.dumps(
            {
                "call_id": await_person_utterance_response.call_id,
                "heard": await_person_utterance_response.heard,
                "text": await_person_utterance_response.text,
            }
        ).encode()

    def deserialize(self, buf: bytes) -> AwaitPersonUtteranceResponse:
        snapshot = json.loads(buf)
        if not (
            isinstance(snapshot, dict)
            and isinstance(snapshot.get("call_id"), str)
            and isinstance(snapshot.get("heard"), str)
            and isinstance(snapshot.get("text"), str)
        ):
            raise errors.invalid(
                "invalid_snapshot", "an await person utterance response is a call_id, what was heard, and a text"
            )
        return AwaitPersonUtteranceResponse(
            call_id=snapshot["call_id"], heard=snapshot["heard"], text=snapshot["text"]
        )


class PersonRelay(ts.Relay, typing.Protocol):

    async def await_person_answered(  # tesser:debt TB085
        self, await_person_answered_request: AwaitPersonAnsweredRequest
    ) -> AwaitPersonAnsweredResponse: ...

    async def await_person_utterance(  # tesser:debt TB085
        self, await_person_utterance_request: AwaitPersonUtteranceRequest
    ) -> AwaitPersonUtteranceResponse: ...
