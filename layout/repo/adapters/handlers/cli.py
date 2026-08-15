from __future__ import annotations

from typing import Final

import tesser.adapters as ts

import repo.client.client as client
from protocol.cli import CliRequest, CliResponse

_CHECK_USAGE: Final[str] = "usage: python -m srv.cli.check <repo-root>"

_TREES_USAGE: Final[str] = "usage: python -m srv.cli.trees <repo-root>"


class Handler(ts.Handler):
    def __init__(self, client: client.Client) -> None:
        self._client = client

    def check(self, req: CliRequest) -> CliResponse:
        root = req.arg(0, "repo-root", _CHECK_USAGE)
        req.no_extra_args(1, _CHECK_USAGE)
        response = self._client.check(client.CheckRequest(root=root))
        if response.problems:
            lines = "\n".join(f"layout: {problem}" for problem in response.problems)
            return CliResponse(1, stdout="", stderr=lines)
        rows, apps = response.counts
        return CliResponse.ok(
            f"layout: {rows} rows, {apps} app trees — disk, declarations, and gates agree"
        )

    def trees(self, req: CliRequest) -> CliResponse:
        root = req.arg(0, "repo-root", _TREES_USAGE)
        req.no_extra_args(1, _TREES_USAGE)
        checked = self._client.check(client.CheckRequest(root=root))
        if checked.problems:
            lines = "\n".join(f"layout: {problem}" for problem in checked.problems)
            return CliResponse(1, stdout="", stderr=lines)
        response = self._client.trees(client.TreesRequest(root=root))
        return CliResponse.ok("\n".join(response.trees))
