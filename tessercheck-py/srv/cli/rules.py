from __future__ import annotations

import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Final

import tesser.srv as ts

import tessercheck.adapters.handlers.cli as cli
from bootstrap.bootstrap import new
from bootstrap.config import from_env
from protocol.cli import CliRequest, CliResponse, UsageError

_USAGE: Final[str] = "usage: python -m srv.cli.rules [tree] [--check]"

_OUTPUT: Final[str] = "RULES.md"

_HERE: Final[str] = "."


@ts.function
def respond(run: Callable[[], CliResponse]) -> CliResponse:
    try:
        return run()
    except UsageError as e:
        return CliResponse(2, stdout="", stderr=f"{e}\n{_USAGE}")
    except Exception:
        return CliResponse(1, stdout="", stderr="unexpected error")


@ts.function
def dispatch(handler: cli.Handler, args: list[str]) -> CliResponse:
    return respond(lambda: handler.rulebook(CliRequest(args=tuple(args))))


@ts.function
def settle(rendered: str, output: Path, check: bool) -> int:
    if check:
        if not output.exists() or output.read_text() != rendered:
            print(
                "RULES.md is stale; regenerate with: python3 -m srv.cli.rules",
                file=sys.stderr,
            )
            return 1
        print("RULES.md is current")
        return 0
    output.write_text(rendered)
    print(f"wrote {output.resolve()}")
    return 0


@ts.function
def run(argv: list[str]) -> int:
    check = "--check" in argv
    args = [arg for arg in argv if arg != "--check"]
    app = new(from_env(os.getenv))
    try:
        resp = dispatch(cli.Handler(app.tessercheck), args)
        if resp.exit_code != 0:
            if resp.stderr:
                print(resp.stderr, file=sys.stderr)
            return resp.exit_code
        root = args[0] if args else _HERE
        return settle(resp.stdout, Path(root) / _OUTPUT, check)
    finally:
        app.close()


if __name__ == "__main__":  # tessercheck:ignore TB051
    raise SystemExit(run(sys.argv[1:]))
