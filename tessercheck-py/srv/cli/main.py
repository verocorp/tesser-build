from __future__ import annotations

import sys
from typing import Final

import tesser.srv as ts

import tessercheck.adapters.handlers.cli as cli
from app.loader import load
from protocol.cli import CliRequest, CliResponse, UsageError

_USAGE: Final[str] = "usage: python -m srv.cli.main [tree]"


def run(argv: list[str]) -> int:  # tesser:debt TB051
    app = load()
    try:
        handler = cli.Handler(app.tessercheck.client)
        try:
            resp = handler.check(CliRequest(args=tuple(argv)))
        except UsageError as e:
            resp = CliResponse(2, stdout="", stderr=f"{e}\n{_USAGE}")
        except Exception:
            resp = CliResponse(1, stdout="", stderr="unexpected error")
        if resp.stdout:
            print(resp.stdout)
        if resp.stderr:
            print(resp.stderr, file=sys.stderr)
        return resp.exit_code
    finally:
        app.close()


if __name__ == "__main__":  # tesser:debt TB051
    raise SystemExit(run(sys.argv[1:]))
