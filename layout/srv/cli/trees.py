from __future__ import annotations

import sys

import tesser.srv as ts

from app.loader import load
import repo.adapters.handlers.cli as cli
from protocol.cli import CliRequest, CliResponse, UsageError

if __name__ == "__main__":  # tesser:debt TB051
    handler = cli.Handler(load().repo.client)
    try:
        response = handler.trees(CliRequest(args=tuple(sys.argv[1:])))
    except UsageError as error:
        response = CliResponse(2, stdout="", stderr=str(error))
    if response.stdout:
        print(response.stdout)
    if response.stderr:
        print(response.stderr, file=sys.stderr)
    raise SystemExit(response.exit_code)
