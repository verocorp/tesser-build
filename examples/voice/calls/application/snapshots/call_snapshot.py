from __future__ import annotations

import json

import tesser.application as ts

import calls.domain as domain
import tesser.errors as errors


class CallSnapshot(ts.Serde):

    def serialize(self, call: domain.Call) -> bytes:
        return json.dumps(
            {
                "call_id": str(call.identity),
                "person": {"name": str(call.person.name), "phone_number": str(call.person.phone_number)},
                "turns": [  # tesser:debt TB082
                    {"speaker": str(turn.speaker), "utterances": [str(u) for u in turn.utterances]}  # tesser:debt TB082
                    for turn in call.conversation.turns
                ],
                "step": str(call.step),
            }
        ).encode()

    def deserialize(self, buf: bytes) -> domain.Call:
        snapshot = json.loads(buf)
        if not (
            isinstance(snapshot, dict)
            and isinstance(snapshot.get("call_id"), str)
            and isinstance(snapshot.get("person"), dict)
            and isinstance(snapshot["person"].get("name"), str)
            and isinstance(snapshot["person"].get("phone_number"), str)
            and isinstance(snapshot.get("turns"), list)
            and all(  # tesser:debt TB082
                isinstance(turn, dict)
                and isinstance(turn.get("speaker"), str)
                and isinstance(turn.get("utterances"), list)
                and all(isinstance(u, str) for u in turn["utterances"])  # tesser:debt TB082
                for turn in snapshot["turns"]
            )
            and isinstance(snapshot.get("step"), str)
        ):
            raise errors.invalid("invalid_snapshot", "a call snapshot is a call_id, a person, its turns, and a step")
        return domain.Call(
            domain.CallSpec(
                call_id=snapshot["call_id"],
                person=domain.PersonSpec(
                    name=snapshot["person"]["name"], phone_number=snapshot["person"]["phone_number"]
                ),
                turns=tuple(  # tesser:debt TB082
                    domain.TurnSpec(speaker=turn["speaker"], utterances=tuple(turn["utterances"]))  # tesser:debt TB082
                    for turn in snapshot["turns"]
                ),
                step=snapshot["step"],
            )
        )
