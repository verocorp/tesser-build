from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class LinkVerdictView:

    slug: str
    target_url: str
    allowed: bool
    reason: str


class Client(Protocol):

    def links_by_verdict(self) -> tuple[LinkVerdictView, ...]: ...
