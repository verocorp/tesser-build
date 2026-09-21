from __future__ import annotations

import json

import tesser.application as ts

import calls.domain as domain
import tesser.errors as errors


class CallSnapshot(ts.Serde):

    def serialize(self, call: domain.Call) -> bytes:
        return json.dumps({"call_id": str(call.identity), "person_name": str(call.person_name)}).encode()

    def deserialize(self, buf: bytes) -> domain.Call:
        snapshot = json.loads(buf)
        if not (
            isinstance(snapshot, dict)
            and isinstance(snapshot.get("call_id"), str)
            and isinstance(snapshot.get("person_name"), str)
        ):
            raise errors.invalid("invalid_snapshot", "a call snapshot is a call_id and a person name")
        return domain.Call(domain.CallSpec(call_id=snapshot["call_id"], person_name=snapshot["person_name"]))
