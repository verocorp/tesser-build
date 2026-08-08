from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

import tesser.srv as ts


class ToolTurn(ts.Response):

    def __init__(self, reply: str, tools: tuple[dict[str, object], ...]) -> None:
        super().__init__(reply=reply, tools=tools)

    reply: str
    tools: tuple[dict[str, object], ...]


class ToolSurface(ts.Port, Protocol):

    def instructions(self) -> str: ...

    def begin(self) -> ToolTurn: ...

    def status(self) -> ToolTurn: ...

    def dispatch(self, tool: str, raw_arguments: Mapping[str, object]) -> ToolTurn: ...
