from __future__ import annotations

import json
import typing

import tesser.application as ts

import calls.application.snapshots as snapshots
import calls.domain as domain
import tesser.errors as errors


class InterpretTurnRequest(ts.Request):
    def __init__(self, call: domain.Call) -> None:
        self.call = call


class InterpretTurnRequestSnapshot(ts.Serde):
    def serialize(self, interpret_turn_request: InterpretTurnRequest) -> bytes:
        return snapshots.CallSnapshot().serialize(interpret_turn_request.call)

    def deserialize(self, buf: bytes) -> InterpretTurnRequest:
        return InterpretTurnRequest(call=snapshots.CallSnapshot().deserialize(buf))


class InterpretTurnResponse(ts.Response):
    def __init__(self, call_id: str, person_names: tuple[str, ...]) -> None:
        self.call_id = call_id
        self.person_names = person_names


class InterpretTurnResponseSnapshot(ts.Serde):
    def serialize(self, interpret_turn_response: InterpretTurnResponse) -> bytes:
        return json.dumps(
            {"call_id": interpret_turn_response.call_id, "person_names": list(interpret_turn_response.person_names)}  # tesser:debt TB082
        ).encode()

    def deserialize(self, buf: bytes) -> InterpretTurnResponse:
        snapshot = json.loads(buf)
        if not (
            isinstance(snapshot, dict)
            and isinstance(snapshot.get("call_id"), str)
            and isinstance(snapshot.get("person_names"), list)
            and all(isinstance(name, str) for name in snapshot["person_names"])  # tesser:debt TB082
        ):
            raise errors.invalid(
                "invalid_snapshot", "an interpretation response is a call_id and a list of person names"
            )
        return InterpretTurnResponse(
            call_id=snapshot["call_id"], person_names=tuple(snapshot["person_names"])  # tesser:debt TB082
        )


class InterpretationRelay(ts.Relay, typing.Protocol):  # tesser:debt TB085
    async def run_interpret_turn(self, interpret_turn_request: InterpretTurnRequest) -> InterpretTurnResponse: ...
