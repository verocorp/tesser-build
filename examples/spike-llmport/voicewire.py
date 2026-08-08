from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

import tesser.srv as ts


class Tool(ts.Record):

    def __init__(self, name: str, description: str, parameters: Mapping[str, object]) -> None:
        super().__init__(name=name, description=description, parameters=dict(parameters))

    name: str
    description: str
    parameters: Mapping[str, object]

    def schema(self) -> dict[str, object]:
        return {"name": self.name, "description": self.description, "parameters": dict(self.parameters)}


class ToolTurn(ts.Response):

    def __init__(self, reply: str, tools: tuple[Tool, ...]) -> None:
        super().__init__(reply=reply, tools=tools)

    reply: str
    tools: tuple[Tool, ...]


class ToolSurface(ts.Port, Protocol):

    def instructions(self) -> str: ...

    def begin(self) -> ToolTurn: ...

    def status(self) -> ToolTurn: ...

    def dispatch(self, tool: str, raw_arguments: Mapping[str, object]) -> ToolTurn: ...
