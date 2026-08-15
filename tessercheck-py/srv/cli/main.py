from __future__ import annotations

import os
import sys
from collections.abc import Callable
from typing import Final

import tesser.srv as ts

import tessercheck.adapters.handlers.cli as cli
from bootstrap.bootstrap import new
from bootstrap.config import from_env
from protocol.cli import CliRequest, CliResponse, UsageError

_USAGE: Final[str] = "usage: python -m srv.cli.main [tree]"


@ts.function
def respond(run: Callable[[], CliResponse]) -> CliResponse:
    try:
        return run()
    except UsageError as e:
        return CliResponse(2, stdout="", stderr=f"{e}\n{_USAGE}")
    except Exception:
        return CliResponse(1, stdout="", stderr="unexpected error")


@ts.function
def dispatch(handler: cli.Handler, argv: list[str]) -> CliResponse:
    return respond(lambda: handler.check(CliRequest(args=tuple(argv))))


@ts.function
def run(argv: list[str]) -> int:
    app = new(from_env(os.getenv))
    try:
        resp = dispatch(cli.Handler(app.tessercheck), argv)
        if resp.stdout:
            print(resp.stdout)
        if resp.stderr:
            print(resp.stderr, file=sys.stderr)
        return resp.exit_code
    finally:
        app.close()


if __name__ == "__main__":  # tessercheck:ignore TB051
    raise SystemExit(run(sys.argv[1:]))
