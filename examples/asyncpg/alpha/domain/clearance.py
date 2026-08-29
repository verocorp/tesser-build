from __future__ import annotations

import enum

import tesser.domain as ts

import tesser.errors as errors
import tesser.serialization as serialization


class Settled(ts.Outcome):
    KEPT = enum.auto()
    DROPPED = enum.auto()


class ClearanceSpec(ts.Spec):

    def __init__(self, verdict: str) -> None:
        self.verdict = verdict


class Clearance(ts.ValueObject):

    _verdict: str

    def __init__(self, spec: ClearanceSpec) -> None:
        if spec.verdict not in ("ok", "refused"):
            raise errors.invalid("invalid_verdict", f"verdict {spec.verdict!r} is not a verdict")
        object.__setattr__(self, "_verdict", spec.verdict)

    def __str__(self) -> str:
        return serialization.canonical_str(self._verdict)

    def settle(self) -> Settled:
        if self._verdict == "ok":
            return Settled.KEPT
        return Settled.DROPPED
