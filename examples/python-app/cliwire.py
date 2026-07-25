from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from errors import DomainError, InfraError, exit_code_for


class UsageError(Exception):
    pass


@dataclass(frozen=True)
class CliRequest:
    args: tuple[str, ...] = ()


@dataclass(frozen=True)
class CliResponse:
    exit_code: int
    stdout: str = ""
    stderr: str = ""


Command = Callable[[CliRequest], CliResponse]


def ok(line: str) -> CliResponse:
    return CliResponse(0, stdout=line)


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


def arg(req: CliRequest, index: int, name: str, usage: str) -> str:
    if index >= len(req.args) or not req.args[index]:
        raise UsageError(f"missing argument <{name}>\n{usage}")
    return req.args[index]


def no_extra_args(req: CliRequest, count: int, usage: str) -> None:
    if len(req.args) > count:
        raise UsageError(f"unexpected extra arguments\n{usage}")
