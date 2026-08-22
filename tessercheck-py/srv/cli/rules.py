from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path
from typing import Final

import tesser.srv as ts

import tessercheck.adapters.handlers.cli as cli
from app.loader import load
from protocol.cli import CliRequest, CliResponse, UsageError

_USAGE: Final[str] = "usage: python -m srv.cli.rules [tree] [--check]"

_OUTPUT: Final[str] = "RULES.md"

_HERE: Final[str] = "."


@ts.do_not_use_function
def respond(run: Callable[[], CliResponse]) -> CliResponse:  # tesser:debt TB051
    try:
        return run()
    except UsageError as e:
        return CliResponse(2, stdout="", stderr=f"{e}\n{_USAGE}")
    except Exception:
        return CliResponse(1, stdout="", stderr="unexpected error")


@ts.do_not_use_function
def dispatch(handler: cli.Handler, args: list[str]) -> CliResponse:  # tesser:debt TB051
    return respond(lambda: handler.rulebook(CliRequest(args=tuple(args))))


@ts.do_not_use_function
def settle(rendered: str, output: Path, check: bool) -> int:  # tesser:debt TB051
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


@ts.do_not_use_function
def run(argv: list[str]) -> int:  # tesser:debt TB051
    check = "--check" in argv
    args = [arg for arg in argv if arg != "--check"]
    app = load()
    try:
        resp = dispatch(cli.Handler(app.tessercheck.client), args)
        if resp.exit_code != 0:
            if resp.stderr:
                print(resp.stderr, file=sys.stderr)
            return resp.exit_code
        root = args[0] if args else _HERE
        return settle(resp.stdout, Path(root) / _OUTPUT, check)
    finally:
        app.close()


if __name__ == "__main__":  # tesser:debt TB051
    raise SystemExit(run(sys.argv[1:]))
