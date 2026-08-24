from __future__ import annotations

import copy
import collections.abc as abc
import typing

import tesser.srv as ts


class BadToolCall(ts.Rejection):
    pass


class Tool(ts.Record):

    def __init__(self, name: str, description: str, parameters: abc.Mapping[str, object]) -> None:
        super().__init__(name=name, description=description, parameters=copy.deepcopy(dict(parameters)))

    name: str
    description: str
    parameters: abc.Mapping[str, object]

    def schema(self) -> dict[str, object]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": copy.deepcopy(dict(self.parameters)),
        }


class ToolCall(ts.Request):

    def __init__(self, name: str, arguments: abc.Mapping[str, object]) -> None:
        super().__init__(name=name, arguments=copy.deepcopy(dict(arguments)))

    name: str
    arguments: abc.Mapping[str, object]

    def text(self, key: str) -> str:
        value = self.arguments.get(key)
        if not isinstance(value, str):
            raise BadToolCall(f"{key} must be a string")
        return value


class ToolTurn(ts.Response):

    def __init__(self, reply: str, tools: tuple[Tool, ...]) -> None:
        super().__init__(reply=reply, tools=tools)

    reply: str
    tools: tuple[Tool, ...]


class ToolEndpoint(ts.Port, typing.Protocol):

    def __call__(self, call: ToolCall, /) -> ToolTurn: ...


class Route(ts.Record):

    def __init__(self, name: str, endpoint: ToolEndpoint) -> None:
        super().__init__(name=name, endpoint=endpoint)

    name: str
    endpoint: ToolEndpoint


class ToolSurface(ts.Port, typing.Protocol):

    def instructions(self) -> str: ...

    def begin(self) -> ToolTurn: ...

    def status(self) -> ToolTurn: ...
