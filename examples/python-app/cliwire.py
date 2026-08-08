from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

import tesser.srv as ts

from errors import DomainError, InfraError, exit_code_for


class UsageError(Exception):
    pass


class CliRequest(ts.Request):

    def __init__(self, args: tuple[str, ...] = ()) -> None:
        super().__init__(args=args)

    args: tuple[str, ...]


class CliResponse(ts.Response):

    def __init__(self, exit_code: int, stdout: str = "", stderr: str = "") -> None:
        super().__init__(exit_code=exit_code, stdout=stdout, stderr=stderr)

    exit_code: int
    stdout: str
    stderr: str


class Command(ts.Port, Protocol):

    def __call__(self, request: CliRequest, /) -> CliResponse: ...


@ts.function
def ok(line: str) -> CliResponse:
    return CliResponse(0, stdout=line)


@ts.function
def respond(run: Callable[[], CliResponse]) -> CliResponse:
    try:
        return run()
    except UsageError as e:
        return CliResponse(2, stderr=str(e))
    except DomainError as e:
        return CliResponse(exit_code_for(e.kind), stderr=f"[{e.code}] {e.message}")
    except InfraError:
        return CliResponse(1, stderr="a dependency is unavailable; please retry")
    except Exception:
        return CliResponse(1, stderr="unexpected error")


@ts.function
def arg(req: CliRequest, index: int, name: str, usage: str) -> str:
    if index >= len(req.args) or not req.args[index]:
        raise UsageError(f"missing argument <{name}>\n{usage}")
    return req.args[index]


@ts.function
def no_extra_args(req: CliRequest, count: int, usage: str) -> None:
    if len(req.args) > count:
        raise UsageError(f"unexpected extra arguments\n{usage}")
