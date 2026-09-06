from __future__ import annotations

import typing

import tesser.adapters as ts

import protocol
import tessercheck.client as client

_CHECK_USAGE: typing.Final[str] = "usage: check [tree]"

_RULES_USAGE: typing.Final[str] = "usage: rules [tree]"

_HERE: typing.Final[str] = "."


class Handler(ts.Handler):

    def __init__(self, tessercheck_client: client.TessercheckClient) -> None:
        self._tessercheck_client = tessercheck_client

    def check(self, cli_request: protocol.CliRequest) -> protocol.CliResponse:
        root = cli_request.arg(0, _HERE)
        cli_request.no_extra_args(1, _CHECK_USAGE)
        check_response = self._tessercheck_client.check(client.CheckRequest(tree=root))
        return protocol.CliResponse(
            1 if check_response.findings else 0,
            stdout="\n".join(check_response.findings),
            stderr="",
        )

    def rulebook(self, cli_request: protocol.CliRequest) -> protocol.CliResponse:
        root = cli_request.arg(0, _HERE)
        cli_request.no_extra_args(1, _RULES_USAGE)
        rulebook_response = self._tessercheck_client.rulebook(client.RulebookRequest(tree=root))
        return protocol.CliResponse(0, stdout=rulebook_response.rendered, stderr="")
