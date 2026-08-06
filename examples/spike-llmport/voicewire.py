from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol


class ToolState(Protocol):

    reply: str


class ToolHandler(Protocol):

    def instructions(self) -> str: ...

    def begin(self) -> ToolState: ...

    def status(self) -> ToolState: ...

    def tools(self, state: ToolState) -> tuple[dict[str, object], ...]: ...

    def dispatch(
        self, tool: str, raw_arguments: Mapping[str, object]
    ) -> ToolState: ...
