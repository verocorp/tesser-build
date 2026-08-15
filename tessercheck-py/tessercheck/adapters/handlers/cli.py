from __future__ import annotations

from typing import Final

import tesser.adapters as ts

import tessercheck.client.client as client
from protocol.cli import CliRequest, CliResponse

_CHECK_USAGE: Final[str] = "usage: check [tree]"

_HERE: Final[str] = "."


class Handler(ts.Handler):

    def __init__(self, client: client.Client) -> None:
        self._client = client

    def check(self, req: CliRequest) -> CliResponse:
        root = req.arg(0, _HERE)
        req.no_extra_args(1, _CHECK_USAGE)
        view = self._client.check(client.CheckRequest(root=root))
        return CliResponse(
            1 if view.findings else 0,
            stdout="\n".join(view.findings),
            stderr="",
        )
