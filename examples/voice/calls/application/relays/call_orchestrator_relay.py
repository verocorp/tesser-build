from __future__ import annotations

import json
import typing

import tesser.application as ts

import calls.application.snapshots as snapshots
import calls.domain as domain
import tesser.errors as errors


class ConductCallRequest(ts.Request):

    def __init__(self, call: domain.Call) -> None:
        self.call = call


class ConductCallRequestSnapshot(ts.Serde):

    def serialize(self, conduct_call_request: ConductCallRequest) -> bytes:
        return snapshots.CallSnapshot().serialize(conduct_call_request.call)

    def deserialize(self, buf: bytes) -> ConductCallRequest:
        return ConductCallRequest(call=snapshots.CallSnapshot().deserialize(buf))


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


class CallOrchestratorRelay(ts.Relay, typing.Protocol):

    async def run_conduct_call(self, conduct_call_request: ConductCallRequest) -> ConductCallResponse: ...

    async def run_person_joined(self, person_joined_request: PersonJoinedRequest) -> PersonJoinedResponse: ...

    async def run_person_turn_completed(
        self, person_turn_completed_request: PersonTurnCompletedRequest
    ) -> PersonTurnCompletedResponse: ...
