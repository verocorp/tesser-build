from __future__ import annotations

import json
import typing

import tesser.application as ts

import tesser.errors as errors


class AwaitPersonJoinedRequest(ts.Request):
    def __init__(self, call_id: str) -> None:
        self.call_id = call_id


class AwaitPersonJoinedResponse(ts.Response):
    def __init__(self, call_id: str) -> None:
        self.call_id = call_id


class AwaitPersonJoinedResponseSnapshot(ts.Serde):
    def serialize(self, await_person_joined_response: AwaitPersonJoinedResponse) -> bytes:
        return json.dumps({"call_id": await_person_joined_response.call_id}).encode()

    def deserialize(self, buf: bytes) -> AwaitPersonJoinedResponse:
        snapshot = json.loads(buf)
        if not (isinstance(snapshot, dict) and isinstance(snapshot.get("call_id"), str)):
            raise errors.invalid("invalid_snapshot", "an await person joined response is a call_id")
        return AwaitPersonJoinedResponse(call_id=snapshot["call_id"])


class AwaitPersonTurnRequest(ts.Request):
    def __init__(self, call_id: str) -> None:
        self.call_id = call_id


class AwaitPersonTurnResponse(ts.Response):
    def __init__(self, call_id: str, text: str) -> None:
        self.call_id = call_id
        self.text = text


class AwaitPersonTurnResponseSnapshot(ts.Serde):
    def serialize(self, await_person_turn_response: AwaitPersonTurnResponse) -> bytes:
        return json.dumps(
            {"call_id": await_person_turn_response.call_id, "text": await_person_turn_response.text}
        ).encode()

    def deserialize(self, buf: bytes) -> AwaitPersonTurnResponse:
        snapshot = json.loads(buf)
        if not (
            isinstance(snapshot, dict)
            and isinstance(snapshot.get("call_id"), str)
            and isinstance(snapshot.get("text"), str)
        ):
            raise errors.invalid("invalid_snapshot", "an await person turn response is a call_id and a text")
        return AwaitPersonTurnResponse(call_id=snapshot["call_id"], text=snapshot["text"])


class PersonRelay(ts.Relay, typing.Protocol):
    async def await_person_joined(  # tesser:debt TB085
        self, await_person_joined_request: AwaitPersonJoinedRequest
    ) -> AwaitPersonJoinedResponse: ...

    async def await_person_turn(  # tesser:debt TB085
        self, await_person_turn_request: AwaitPersonTurnRequest
    ) -> AwaitPersonTurnResponse: ...
