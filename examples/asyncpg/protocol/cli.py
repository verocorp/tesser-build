from __future__ import annotations

import typing

import tesser.srv as ts


class UsageError(ts.Rejection):
    pass


class Line(ts.Record):

    def __init__(self, text: str) -> None:
        super().__init__(text=text)

    text: str


class CliRequest(ts.Request):

    def __init__(self, args: tuple[str, ...]) -> None:
        super().__init__(args=args)

    args: tuple[str, ...]

    def arg(self, index: int, name: str, usage: str) -> str:
        if index >= len(self.args) or not self.args[index]:
            raise UsageError(f"missing argument <{name}>\n{usage}")
        return self.args[index]


class CliResponse(ts.Response):

    def __init__(self, exit_code: int, line: Line) -> None:
        super().__init__(exit_code=exit_code, line=line)

    exit_code: int
    line: Line


class Command(ts.Port, typing.Protocol):

    def __call__(self, request: CliRequest, /) -> CliResponse: ...
