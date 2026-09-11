from __future__ import annotations

import typing

import tesser.adapters as ts

import alpha.client as client
import protocol

_ADD_USAGE: typing.Final[str] = "usage: add <name> <part>"


class Handler(ts.Handler):

    def __init__(self, alpha_client: client.AlphaClient) -> None:
        self._alpha_client = alpha_client

    async def add(self, cli_request: protocol.CliRequest) -> protocol.CliResponse:
        name = cli_request.arg(0, "name", _ADD_USAGE)
        part = cli_request.arg(1, "part", _ADD_USAGE)
        try:
            add_response = await self._alpha_client.add(client.AddRequest(name=name, part=part))
        except client.ERRORS as error:
            match error:
                case client.Rejected():
                    return protocol.CliResponse(
                        exit_code=2, line=protocol.Line(text=error.message)
                    )
                case client.Missing():
                    return protocol.CliResponse(
                        exit_code=1, line=protocol.Line(text=error.message)
                    )
                case client.Conflict():
                    return protocol.CliResponse(
                        exit_code=1, line=protocol.Line(text=error.message)
                    )
                case _ as never:
                    typing.assert_never(never)
        return protocol.CliResponse(
            exit_code=0,
            line=protocol.Line(
                text=f"{add_response.name} {add_response.part} {add_response.standing}"
            ),
        )
