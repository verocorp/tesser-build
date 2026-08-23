from __future__ import annotations

import sys

import tesser.srv as ts

from app.loader import load
import repo.adapters.handlers.cli as cli
from protocol.cli import CliRequest, CliResponse, UsageError

class CheckHost(ts.Host):

    def run(self, argv: list[str]) -> int:
        handler = cli.Handler(load().repo.client)
        try:
            response = handler.check(CliRequest(args=tuple(argv)))
        except UsageError as error:
            response = CliResponse(2, stdout="", stderr=str(error))
        if response.stdout:
            print(response.stdout)
        if response.stderr:
            print(response.stderr, file=sys.stderr)
        return response.exit_code


if __name__ == "__main__":
    ts.main(CheckHost().run)
