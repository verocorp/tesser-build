from __future__ import annotations

import copy
from collections.abc import Mapping
from typing import Protocol

import tesser.srv as ts


class Tool(ts.Record):

    def __init__(self, name: str, description: str, parameters: Mapping[str, object]) -> None:
        super().__init__(name=name, description=description, parameters=copy.deepcopy(dict(parameters)))

    name: str
    description: str
    parameters: Mapping[str, object]

    def schema(self) -> dict[str, object]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": copy.deepcopy(dict(self.parameters)),
        }


class ToolCall(ts.Request):

    def __init__(self, name: str, arguments: Mapping[str, object]) -> None:
        super().__init__(name=name, arguments=copy.deepcopy(dict(arguments)))

    name: str
    arguments: Mapping[str, object]


class ToolTurn(ts.Response):

    def __init__(self, reply: str, tools: tuple[Tool, ...]) -> None:
        super().__init__(reply=reply, tools=tools)

    reply: str
    tools: tuple[Tool, ...]


class ToolEndpoint(ts.Port, Protocol):

    def __call__(self, call: ToolCall, /) -> ToolTurn: ...


class Route(ts.Record):

    def __init__(self, name: str, endpoint: ToolEndpoint) -> None:
        super().__init__(name=name, endpoint=endpoint)

    name: str
    endpoint: ToolEndpoint


class ToolSurface(ts.Port, Protocol):

    def instructions(self) -> str: ...

    def begin(self) -> ToolTurn: ...

    def status(self) -> ToolTurn: ...
