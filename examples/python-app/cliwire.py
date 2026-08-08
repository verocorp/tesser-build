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

    def arg(self, index: int, name: str, usage: str) -> str:
        if index >= len(self.args) or not self.args[index]:
            raise UsageError(f"missing argument <{name}>\n{usage}")
        return self.args[index]

    def no_extra_args(self, count: int, usage: str) -> None:
        if len(self.args) > count:
            raise UsageError(f"unexpected extra arguments\n{usage}")


class CliResponse(ts.Response):

    def __init__(self, exit_code: int, stdout: str = "", stderr: str = "") -> None:
        super().__init__(exit_code=exit_code, stdout=stdout, stderr=stderr)

    exit_code: int
    stdout: str
    stderr: str

    @classmethod
    def ok(cls, line: str) -> CliResponse:
        return cls(0, stdout=line)

    @classmethod
    def respond(cls, run: Callable[[], CliResponse]) -> CliResponse:
        try:
            return run()
        except UsageError as e:
            return cls(2, stderr=str(e))
        except DomainError as e:
            return cls(exit_code_for(e.kind), stderr=f"[{e.code}] {e.message}")
        except InfraError:
            return cls(1, stderr="a dependency is unavailable; please retry")
        except Exception:
            return cls(1, stderr="unexpected error")


class Command(ts.Port, Protocol):

    def __call__(self, request: CliRequest, /) -> CliResponse: ...
