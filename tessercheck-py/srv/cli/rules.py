from __future__ import annotations

import sys
import pathlib
import typing

import tesser.srv as ts

import tessercheck.adapters.handlers.cli as cli
import app.loader as loader
import protocol.cli as protocol_cli

_USAGE: typing.Final[str] = "usage: python -m srv.cli.rules [tree] [--check]"

_OUTPUT: typing.Final[str] = "RULES.md"

_HERE: typing.Final[str] = "."


class RulesHost(ts.Host):

    def run(self, argv: list[str]) -> int:
        check = "--check" in argv
        args = [arg for arg in argv if arg != "--check"]
        app = loader.load()
        try:
            handler = cli.Handler(app.tessercheck.client)
            try:
                resp = handler.rulebook(protocol_cli.CliRequest(args=tuple(args)))
            except protocol_cli.UsageError as e:
                resp = protocol_cli.CliResponse(2, stdout="", stderr=f"{e}\n{_USAGE}")
            except Exception:
                resp = protocol_cli.CliResponse(1, stdout="", stderr="unexpected error")
            if resp.exit_code != 0:
                if resp.stderr:
                    print(resp.stderr, file=sys.stderr)
                return resp.exit_code
            root = args[0] if args else _HERE
            output = pathlib.Path(root) / _OUTPUT
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
    ts.main(RulesHost().run)
