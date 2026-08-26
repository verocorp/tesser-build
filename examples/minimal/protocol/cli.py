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


class CliResponse(ts.Response):

    def __init__(self, exit_code: int, line: Line) -> None:
        super().__init__(exit_code=exit_code, line=line)

    exit_code: int
    line: Line


class Command(ts.Port, typing.Protocol):

    def __call__(self, request: CliRequest, /) -> CliResponse: ...
