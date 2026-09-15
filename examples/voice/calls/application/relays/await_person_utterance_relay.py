from __future__ import annotations

import json
import typing

import tesser.application as ts

import tesser.errors as errors


class AwaitPersonUtteranceRequest(ts.Request):

    def __init__(self, call_id: str) -> None:
        self.call_id = call_id


class AwaitPersonUtteranceRequestSnapshot(ts.Serde):

    def serialize(self, await_person_utterance_request: AwaitPersonUtteranceRequest) -> bytes:
        return json.dumps({"call_id": await_person_utterance_request.call_id}).encode()

    def deserialize(self, buf: bytes) -> AwaitPersonUtteranceRequest:
        snapshot = json.loads(buf)
        if not (isinstance(snapshot, dict) and isinstance(snapshot.get("call_id"), str)):
            raise errors.invalid("invalid_snapshot", "an await person utterance request is a call_id")
        return AwaitPersonUtteranceRequest(call_id=snapshot["call_id"])


class AwaitPersonUtteranceResponse(ts.Response):

    def __init__(self, call_id: str, text: str) -> None:
        self.call_id = call_id
        self.text = text


class AwaitPersonUtteranceResponseSnapshot(ts.Serde):

    def serialize(self, await_person_utterance_response: AwaitPersonUtteranceResponse) -> bytes:
        return json.dumps(
            {"call_id": await_person_utterance_response.call_id, "text": await_person_utterance_response.text}
        ).encode()

    def deserialize(self, buf: bytes) -> AwaitPersonUtteranceResponse:
        snapshot = json.loads(buf)
        if not (
            isinstance(snapshot, dict)
            and isinstance(snapshot.get("call_id"), str)
            and isinstance(snapshot.get("text"), str)
        ):
            raise errors.invalid("invalid_snapshot", "an await person utterance response is a call_id and a text")
        return AwaitPersonUtteranceResponse(call_id=snapshot["call_id"], text=snapshot["text"])


class AwaitPersonUtteranceRelay(ts.Relay, typing.Protocol):

    async def await_person_utterance(  # tesser:debt TB085
        self, await_person_utterance_request: AwaitPersonUtteranceRequest
    ) -> AwaitPersonUtteranceResponse: ...
