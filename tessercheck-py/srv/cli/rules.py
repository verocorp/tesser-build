from __future__ import annotations

import sys
from pathlib import Path
from typing import Final

import tesser.srv as ts

import tessercheck.adapters.handlers.cli as cli
from app.loader import load
from protocol.cli import CliRequest, CliResponse, UsageError

_USAGE: Final[str] = "usage: python -m srv.cli.rules [tree] [--check]"

_OUTPUT: Final[str] = "RULES.md"

_HERE: Final[str] = "."


def run(argv: list[str]) -> int:  # tesser:debt TB051
    check = "--check" in argv
    args = [arg for arg in argv if arg != "--check"]
    app = load()
    try:
        handler = cli.Handler(app.tessercheck.client)
        try:
            resp = handler.rulebook(CliRequest(args=tuple(args)))
        except UsageError as e:
            resp = CliResponse(2, stdout="", stderr=f"{e}\n{_USAGE}")
        except Exception:
            resp = CliResponse(1, stdout="", stderr="unexpected error")
        if resp.exit_code != 0:
            if resp.stderr:
                print(resp.stderr, file=sys.stderr)
            return resp.exit_code
        root = args[0] if args else _HERE
        output = Path(root) / _OUTPUT
        if check:
            if not output.exists() or output.read_text() != resp.stdout:
                print(
                    "RULES.md is stale; regenerate with: python3 -m srv.cli.rules",
                    file=sys.stderr,
                )
                return 1
            print("RULES.md is current")
            return 0
        output.write_text(resp.stdout)
        print(f"wrote {output.resolve()}")
        return 0
    finally:
        app.close()


if __name__ == "__main__":
    ts.main(run)
