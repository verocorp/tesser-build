from __future__ import annotations

import sys

import tesser.srv as ts

from bootstrap.bootstrap import new
import repo.adapters.handlers.cli as cli
from protocol.cli import CliRequest, CliResponse, UsageError


@ts.function
def respond(handler: cli.Handler, argv: list[str]) -> CliResponse:
    try:
        return handler.check(CliRequest(args=tuple(argv)))
    except UsageError as error:
        return CliResponse(2, stdout="", stderr=str(error))


@ts.function
def run(argv: list[str]) -> int:
    response = respond(cli.Handler(new().repo), argv)
    if response.stdout:
        print(response.stdout)
    if response.stderr:
        print(response.stderr, file=sys.stderr)
    return response.exit_code


if __name__ == "__main__":  # tessercheck:ignore TB051
    raise SystemExit(run(sys.argv[1:]))
