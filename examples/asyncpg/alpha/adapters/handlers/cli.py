from __future__ import annotations

import typing

import tesser.adapters as ts

import alpha.client.client as client
import protocol.cli as cli

_ADD_USAGE: typing.Final[str] = "usage: add <name> <part>"


class Handler(ts.Handler):

    def __init__(self, client: client.Client) -> None:
        self._client = client

    async def add(self, request: cli.CliRequest) -> cli.CliResponse:
        name = request.arg(0, "name", _ADD_USAGE)
        part = request.arg(1, "part", _ADD_USAGE)
        added = await self._client.add(client.AddRequest(name=name, part=part))
        return cli.CliResponse(
            exit_code=0, line=cli.Line(text=f"{added.name} {added.part} {added.standing}")
        )
