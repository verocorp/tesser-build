from __future__ import annotations

import typing

import tesser.adapters as ts

import alpha.client as client
import protocol

_ADD_USAGE: typing.Final[str] = "usage: add <name> <part>"
_CREATE_USAGE: typing.Final[str] = "usage: create <name>"
_APPROVE_USAGE: typing.Final[str] = "usage: approve <name>"
_FIND_USAGE: typing.Final[str] = "usage: find <name>"


class Handler(ts.Handler):

    def __init__(self, alpha_client: client.AlphaClient) -> None:
        self._alpha_client = alpha_client

    async def add_part(self, cli_request: protocol.CliRequest) -> protocol.CliResponse:
        name = cli_request.arg(0, "name", _ADD_USAGE)
        part = cli_request.arg(1, "part", _ADD_USAGE)
        try:
            add_part_response = await self._alpha_client.add_part(client.AddPartRequest(name=name, part=part))
        except client.ERRORS as error:
            match error:
                case client.WidgetRejected():
                    return protocol.CliResponse(exit_code=2, line=protocol.Line(text=error.message))
                case _ as never:
                    typing.assert_never(never)
        return protocol.CliResponse(exit_code=0, line=protocol.Line(text=add_part_response.name))

    async def create_widget(self, cli_request: protocol.CliRequest) -> protocol.CliResponse:
        name = cli_request.arg(0, "name", _CREATE_USAGE)
        try:
            create_widget_response = await self._alpha_client.create_widget(client.CreateWidgetRequest(name=name))
        except client.ERRORS as error:
            match error:
                case client.WidgetRejected():
                    return protocol.CliResponse(exit_code=2, line=protocol.Line(text=error.message))
                case _ as never:
                    typing.assert_never(never)
        return protocol.CliResponse(exit_code=0, line=protocol.Line(text=create_widget_response.name))

    async def approve_widget(self, cli_request: protocol.CliRequest) -> protocol.CliResponse:
        name = cli_request.arg(0, "name", _APPROVE_USAGE)
        try:
            approve_widget_response = await self._alpha_client.approve_widget(client.ApproveWidgetRequest(name=name))
        except client.ERRORS as error:
            match error:
                case client.WidgetRejected():
                    return protocol.CliResponse(exit_code=2, line=protocol.Line(text=error.message))
                case _ as never:
                    typing.assert_never(never)
        return protocol.CliResponse(exit_code=0, line=protocol.Line(text=approve_widget_response.name))

    async def find_widget(self, cli_request: protocol.CliRequest) -> protocol.CliResponse:
        name = cli_request.arg(0, "name", _FIND_USAGE)
        try:
            find_widget_response = await self._alpha_client.find_widget(client.FindWidgetRequest(name=name))
        except client.ERRORS as error:
            match error:
                case client.WidgetRejected():
                    return protocol.CliResponse(exit_code=2, line=protocol.Line(text=error.message))
                case _ as never:
                    typing.assert_never(never)
        return protocol.CliResponse(exit_code=0, line=protocol.Line(text=find_widget_response.found))
