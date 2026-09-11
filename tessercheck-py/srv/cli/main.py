from __future__ import annotations

import sys
import typing

import tesser.srv as ts

import app
import protocol
import tessercheck.adapters.handlers as tessercheck_handlers

_USAGE: typing.Final[str] = "usage: python -m srv.cli.main [tree]"


class MainHost(ts.Host):

    def run(self, argv: list[str]) -> int:
        tessercheck_app = app.load()
        try:
            handler = tessercheck_handlers.Handler(tessercheck_app.tessercheck.client)
            try:
                resp = handler.check(protocol.CliRequest(args=tuple(argv)))
            except protocol.UsageError as e:
                resp = protocol.CliResponse(2, stdout="", stderr=f"{e}\n{_USAGE}")
            except Exception:
                resp = protocol.CliResponse(1, stdout="", stderr="unexpected error")
            if resp.stdout:
                print(resp.stdout)
            if resp.stderr:
                print(resp.stderr, file=sys.stderr)
            return resp.exit_code
        finally:
            tessercheck_app.close()


if __name__ == "__main__":
    ts.main(MainHost().run)
