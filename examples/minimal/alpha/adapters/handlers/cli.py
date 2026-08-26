from __future__ import annotations

import typing

import tesser.adapters as ts

import alpha.client.client as client
import protocol.cli as cli

_ADD_USAGE: typing.Final[str] = "usage: add <name>"


class Handler(ts.Handler):

    def __init__(self, client: client.Client) -> None:
        self._client = client

    def add(self, request: cli.CliRequest) -> cli.CliResponse:
        name = request.arg(0, "name", _ADD_USAGE)
        added = self._client.add(client.AddRequest(name=name))
        return cli.CliResponse(exit_code=0, line=cli.Line(text=added.name))
