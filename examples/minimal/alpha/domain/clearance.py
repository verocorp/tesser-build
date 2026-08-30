from __future__ import annotations

import enum

import tesser.domain as ts

import tesser.errors as errors
import tesser.serialization as serialization


class Verdict(ts.Outcome):
    CLEARED = enum.auto()
    REFUSED = enum.auto()


class ClearanceSpec(ts.Spec):

    def __init__(self, verdict: str) -> None:
        self.verdict = verdict


class Clearance(ts.ValueObject):

    _verdict: str

    def __init__(self, spec: ClearanceSpec) -> None:
        if spec.verdict not in ("ok", "refused"):
            raise errors.invalid("invalid_verdict", f"verdict {spec.verdict!r} is not a verdict")
        object.__setattr__(self, "_verdict", spec.verdict)

    def decide(self) -> Verdict:
        if self._verdict == "ok":
            return Verdict.CLEARED
        return Verdict.REFUSED

    def __str__(self) -> str:
        return serialization.canonical_str(self._verdict)


class Standing(ts.ValueObject):

    _value: str

    def __init__(self, value: str) -> None:
        if value not in ("kept", "released"):
            raise errors.invalid("invalid_standing", f"standing {value!r} is not a standing")
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return serialization.canonical_str(self._value)
