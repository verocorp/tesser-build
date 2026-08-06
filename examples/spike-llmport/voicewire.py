from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol, TypeVar


class ToolState(Protocol):

    reply: str


S = TypeVar("S", bound=ToolState)


class ToolHandler(Protocol[S]):

    def instructions(self) -> str: ...

    def begin(self) -> S: ...

    def status(self) -> S: ...

    def tools(self, state: S) -> tuple[dict[str, object], ...]: ...

    def dispatch(self, tool: str, raw_arguments: Mapping[str, object]) -> S: ...
