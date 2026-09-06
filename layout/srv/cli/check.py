from __future__ import annotations

import sys

import tesser.srv as ts

import app
import protocol
import repo.adapters.handlers as handlers


class CheckHost(ts.Host):

    def run(self, argv: list[str]) -> int:
        layout_app = app.load()
        handler = handlers.Handler(layout_app.repo.client)
        try:
            cli_response = handler.check(protocol.CliRequest(args=tuple(argv)))
        except protocol.UsageError as error:
            cli_response = protocol.CliResponse(2, stdout="", stderr=str(error))
        if cli_response.stdout:
            print(cli_response.stdout)
        if cli_response.stderr:
            print(cli_response.stderr, file=sys.stderr)
        return cli_response.exit_code


if __name__ == "__main__":
    ts.main(CheckHost().run)
