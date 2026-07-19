from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class CheckRequest:
    target_url: str


@dataclass(frozen=True)
class CheckResponse:
    allowed: bool
    reason: str


@dataclass(frozen=True)
class VerdictView:

    target_url: str
    allowed: bool
    reason: str


class Client(Protocol):

    def check(self, req: CheckRequest) -> CheckResponse: ...

    def list_verdicts(self) -> tuple[VerdictView, ...]: ...
