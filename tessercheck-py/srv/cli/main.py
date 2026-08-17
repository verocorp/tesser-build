from __future__ import annotations

import sys
from collections.abc import Callable
from typing import Final

import tesser.srv as ts

import tessercheck.adapters.handlers.cli as cli
from app.loader import load
from protocol.cli import CliRequest, CliResponse, UsageError

_USAGE: Final[str] = "usage: python -m srv.cli.main [tree]"


@ts.do_not_use_function
def respond(run: Callable[[], CliResponse]) -> CliResponse:
    try:
        return run()
    except UsageError as e:
        return CliResponse(2, stdout="", stderr=f"{e}\n{_USAGE}")
    except Exception:
        return CliResponse(1, stdout="", stderr="unexpected error")


@ts.do_not_use_function
def dispatch(handler: cli.Handler, argv: list[str]) -> CliResponse:
    return respond(lambda: handler.check(CliRequest(args=tuple(argv))))


@ts.do_not_use_function
def run(argv: list[str]) -> int:
    app = load()
    try:
        resp = dispatch(cli.Handler(app.tessercheck.client), argv)
        if resp.stdout:
            print(resp.stdout)
        if resp.stderr:
            print(resp.stderr, file=sys.stderr)
        return resp.exit_code
    finally:
        app.close()


if __name__ == "__main__":  # tessercheck:ignore TB051
    raise SystemExit(run(sys.argv[1:]))
