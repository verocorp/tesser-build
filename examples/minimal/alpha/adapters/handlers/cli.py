from __future__ import annotations

import tesser.adapters as ts

import alpha.client.client as client
import protocol.cli as cli
import tesser.errors as errors


class Handler(ts.Handler):

    def __init__(self, client: client.Client) -> None:
        self._client = client

    def add(self, request: cli.CliRequest) -> cli.CliResponse:
        if len(request.args) != 1:
            raise cli.UsageError("usage: add <name>")
        try:
            added = self._client.add(client.AddRequest(name=request.args[0]))
        except errors.DomainError as e:
            return cli.CliResponse(exit_code=errors.exit_code_for(e.kind), line=cli.Line(text=e.message))
        return cli.CliResponse(exit_code=0, line=cli.Line(text=added.name))
