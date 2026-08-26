from __future__ import annotations

import tesser.adapters as ts

import alpha.client.client as client
import protocol.cli as cli
import tesser.errors as errors


class Handler(ts.Handler):

    def __init__(self, client: client.Client) -> None:
        self._client = client

    def add(self, request: cli.CliRequest) -> cli.CliResponse:
        if len(request.args) != 3:
            raise cli.UsageError("usage: add <id> <name> <count>")
        id, name, raw_count = request.args
        try:
            count = int(raw_count)
        except ValueError:
            raise cli.UsageError("count must be an integer") from None
        view = self._client.add(client.AddRequest(id=id, name=name, count=count))
        added = ", ".join(whole.id for whole in view.wholes)
        return cli.CliResponse(exit_code=0, line=cli.Line(text=added))

    def get(self, request: cli.CliRequest) -> cli.CliResponse:
        if len(request.args) != 1:
            raise cli.UsageError("usage: get <id>")
        try:
            view = self._client.get(client.GetRequest(id=request.args[0]))
        except errors.DomainError as e:
            return cli.CliResponse(exit_code=errors.exit_code_for(e.kind), line=cli.Line(text=e.message))
        found = ", ".join(whole.name for whole in view.wholes)
        return cli.CliResponse(exit_code=0, line=cli.Line(text=found))
