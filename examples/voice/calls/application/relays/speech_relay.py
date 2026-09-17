from __future__ import annotations

import json
import typing

import tesser.application as ts

import calls.application.snapshots as snapshots
import calls.domain as domain
import tesser.errors as errors


class SpeakTurnRequest(ts.Request):

    def __init__(self, call: domain.Call) -> None:
        self.call = call


class SpeakTurnRequestSnapshot(ts.Serde):

    def serialize(self, speak_turn_request: SpeakTurnRequest) -> bytes:
        return snapshots.CallSnapshot().serialize(speak_turn_request.call)

    def deserialize(self, buf: bytes) -> SpeakTurnRequest:
        return SpeakTurnRequest(call=snapshots.CallSnapshot().deserialize(buf))


class SpeakTurnResponse(ts.Response):

    def __init__(self, call_id: str, text: str, person_names: tuple[str, ...]) -> None:
        self.call_id = call_id
        self.text = text
        self.person_names = person_names


class SpeakTurnResponseSnapshot(ts.Serde):

    def serialize(self, speak_turn_response: SpeakTurnResponse) -> bytes:
        return json.dumps(
            {
                "call_id": speak_turn_response.call_id,
                "text": speak_turn_response.text,
                "person_names": list(speak_turn_response.person_names),  # tesser:debt TB082
            }
        ).encode()

    def deserialize(self, buf: bytes) -> SpeakTurnResponse:
        snapshot = json.loads(buf)
        if not (
            isinstance(snapshot, dict)
            and isinstance(snapshot.get("call_id"), str)
            and isinstance(snapshot.get("text"), str)
            and isinstance(snapshot.get("person_names"), list)
            and all(isinstance(person_name, str) for person_name in snapshot["person_names"])  # tesser:debt TB082
        ):
            raise errors.invalid(
                "invalid_snapshot", "a speak turn response is a call_id, a text, and the person names given"
            )
        return SpeakTurnResponse(
            call_id=snapshot["call_id"], text=snapshot["text"], person_names=tuple(snapshot["person_names"])  # tesser:debt TB082
        )


class EndPersonTurnRequest(ts.Request):

    def __init__(self, call: domain.Call) -> None:
        self.call = call


class EndPersonTurnRequestSnapshot(ts.Serde):

    def serialize(self, end_person_turn_request: EndPersonTurnRequest) -> bytes:
        return snapshots.CallSnapshot().serialize(end_person_turn_request.call)

    def deserialize(self, buf: bytes) -> EndPersonTurnRequest:
        return EndPersonTurnRequest(call=snapshots.CallSnapshot().deserialize(buf))


class EndPersonTurnResponse(ts.Response):

    def __init__(self, call_id: str) -> None:
        self.call_id = call_id


class EndPersonTurnResponseSnapshot(ts.Serde):

    def serialize(self, end_person_turn_response: EndPersonTurnResponse) -> bytes:
        return json.dumps({"call_id": end_person_turn_response.call_id}).encode()

    def deserialize(self, buf: bytes) -> EndPersonTurnResponse:
        snapshot = json.loads(buf)
        if not (isinstance(snapshot, dict) and isinstance(snapshot.get("call_id"), str)):
            raise errors.invalid("invalid_snapshot", "an end person turn response is a call_id")
        return EndPersonTurnResponse(call_id=snapshot["call_id"])


class SpeechRelay(ts.Relay, typing.Protocol):  # tesser:debt TB085

    async def run_speak_turn(self, speak_turn_request: SpeakTurnRequest) -> SpeakTurnResponse: ...

    async def run_end_person_turn(self, end_person_turn_request: EndPersonTurnRequest) -> EndPersonTurnResponse: ...
