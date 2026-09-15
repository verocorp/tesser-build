from __future__ import annotations

import json
import typing

import tesser.application as ts

import tesser.errors as errors


class PersonUtteranceRequest(ts.Request):

    def __init__(self, call_id: str, text: str) -> None:
        self.call_id = call_id
        self.text = text


class PersonUtteranceRequestSnapshot(ts.Serde):

    def serialize(self, person_utterance_request: PersonUtteranceRequest) -> bytes:
        return json.dumps(
            {"call_id": person_utterance_request.call_id, "text": person_utterance_request.text}
        ).encode()

    def deserialize(self, buf: bytes) -> PersonUtteranceRequest:
        snapshot = json.loads(buf)
        if not (
            isinstance(snapshot, dict)
            and isinstance(snapshot.get("call_id"), str)
            and isinstance(snapshot.get("text"), str)
        ):
            raise errors.invalid("invalid_snapshot", "a person utterance request is a call_id and a text")
        return PersonUtteranceRequest(call_id=snapshot["call_id"], text=snapshot["text"])


class PersonUtteranceResponse(ts.Response):

    def __init__(self, call_id: str) -> None:
        self.call_id = call_id


class PersonUtteranceResponseSnapshot(ts.Serde):

    def serialize(self, person_utterance_response: PersonUtteranceResponse) -> bytes:
        return json.dumps({"call_id": person_utterance_response.call_id}).encode()

    def deserialize(self, buf: bytes) -> PersonUtteranceResponse:
        snapshot = json.loads(buf)
        if not (isinstance(snapshot, dict) and isinstance(snapshot.get("call_id"), str)):
            raise errors.invalid("invalid_snapshot", "a person utterance response is a call_id")
        return PersonUtteranceResponse(call_id=snapshot["call_id"])


class PersonUtteranceRelay(ts.Relay, typing.Protocol):

    async def run_person_utterance(
        self, person_utterance_request: PersonUtteranceRequest
    ) -> PersonUtteranceResponse: ...
