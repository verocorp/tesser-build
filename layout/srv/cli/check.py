from __future__ import annotations

import sys

import tesser.srv as ts

import app.loader as loader
import repo.adapters.handlers.cli as cli
import protocol.cli as protocol_cli

class CheckHost(ts.Host):

    def run(self, argv: list[str]) -> int:
        handler = cli.Handler(loader.load().repo.client)
        try:
            response = handler.check(protocol_cli.CliRequest(args=tuple(argv)))
        except protocol_cli.UsageError as error:
            response = protocol_cli.CliResponse(2, stdout="", stderr=str(error))
        if response.stdout:
            print(response.stdout)
        if response.stderr:
            print(response.stderr, file=sys.stderr)
        return response.exit_code


if __name__ == "__main__":
    ts.main(CheckHost().run)
