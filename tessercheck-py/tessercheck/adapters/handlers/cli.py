from __future__ import annotations

import typing

import tesser.adapters as ts

import tessercheck.client.client as client
import protocol.cli as cli

_CHECK_USAGE: typing.Final[str] = "usage: check [tree]"

_RULES_USAGE: typing.Final[str] = "usage: rules [tree]"

_HERE: typing.Final[str] = "."


class Handler(ts.Handler):

    def __init__(self, client: client.Client) -> None:
        self._client = client

    def check(self, req: cli.CliRequest) -> cli.CliResponse:
        root = req.arg(0, _HERE)
        req.no_extra_args(1, _CHECK_USAGE)
        view = self._client.check(client.CheckRequest(tree=root))
        return cli.CliResponse(
            1 if view.findings else 0,
            stdout="\n".join(view.findings),
            stderr="",
        )

    def rulebook(self, req: cli.CliRequest) -> cli.CliResponse:
        root = req.arg(0, _HERE)
        req.no_extra_args(1, _RULES_USAGE)
        view = self._client.rulebook(client.RulebookRequest(tree=root))
        return cli.CliResponse(0, stdout=view.rendered, stderr="")
