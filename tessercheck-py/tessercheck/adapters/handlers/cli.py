from __future__ import annotations

import typing

import tesser.adapters as ts

import protocol.cli as cli
import tessercheck.client as client

_CHECK_USAGE: typing.Final[str] = "usage: check [tree]"

_RULES_USAGE: typing.Final[str] = "usage: rules [tree]"

_HERE: typing.Final[str] = "."


class Handler(ts.Handler):

    def __init__(self, tessercheck_client: client.TessercheckClient) -> None:
        self._tessercheck_client = tessercheck_client

    def check(self, cli_request: cli.CliRequest) -> cli.CliResponse:
        root = cli_request.arg(0, _HERE)
        cli_request.no_extra_args(1, _CHECK_USAGE)
        view = self._tessercheck_client.check(client.CheckRequest(tree=root))
        return cli.CliResponse(
            1 if view.findings else 0,
            stdout="\n".join(view.findings),
            stderr="",
        )

    def rulebook(self, cli_request: cli.CliRequest) -> cli.CliResponse:
        root = cli_request.arg(0, _HERE)
        cli_request.no_extra_args(1, _RULES_USAGE)
        view = self._tessercheck_client.rulebook(client.RulebookRequest(tree=root))
        return cli.CliResponse(0, stdout=view.rendered, stderr="")
