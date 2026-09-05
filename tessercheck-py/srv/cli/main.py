from __future__ import annotations

import sys
import typing

import tesser.srv as ts

import app.loader as loader
import protocol.cli as protocol_cli
import tessercheck.adapters.handlers as handlers

_USAGE: typing.Final[str] = "usage: python -m srv.cli.main [tree]"


class MainHost(ts.Host):

    def run(self, argv: list[str]) -> int:
        app = loader.load()
        try:
            handler = handlers.Handler(app.tessercheck.client)
            try:
                resp = handler.check(protocol_cli.CliRequest(args=tuple(argv)))
            except protocol_cli.UsageError as e:
                resp = protocol_cli.CliResponse(2, stdout="", stderr=f"{e}\n{_USAGE}")
            except Exception:
                resp = protocol_cli.CliResponse(1, stdout="", stderr="unexpected error")
            if resp.stdout:
                print(resp.stdout)
            if resp.stderr:
                print(resp.stderr, file=sys.stderr)
            return resp.exit_code
        finally:
            app.close()


if __name__ == "__main__":
    ts.main(MainHost().run)
