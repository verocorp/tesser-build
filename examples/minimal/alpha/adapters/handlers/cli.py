from __future__ import annotations

import typing

import tesser.adapters as ts

import alpha.client as client
import protocol.cli as cli

_ADD_USAGE: typing.Final[str] = "usage: add <name> <part>"


class Handler(ts.Handler):

    def __init__(self, alpha_client: client.Client) -> None:
        self._alpha_client = alpha_client

    def add(self, cli_request: cli.CliRequest) -> cli.CliResponse:
        name = cli_request.arg(0, "name", _ADD_USAGE)
        part = cli_request.arg(1, "part", _ADD_USAGE)
        add_response = self._alpha_client.add(client.AddRequest(name=name, part=part))
        return cli.CliResponse(exit_code=0, line=cli.Line(text=add_response.name))
