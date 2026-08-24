from __future__ import annotations

import typing

import tesser.adapters as ts

import repo.client.client as client
import protocol.cli as cli

_CHECK_USAGE: typing.Final[str] = "usage: python -m srv.cli.check <repo-root>"

_TREES_USAGE: typing.Final[str] = "usage: python -m srv.cli.trees <repo-root>"


class Handler(ts.Handler):
    def __init__(self, client: client.Client) -> None:
        self._client = client

    def check(self, req: cli.CliRequest) -> cli.CliResponse:
        root = req.arg(0, "repo-root", _CHECK_USAGE)
        req.no_extra_args(1, _CHECK_USAGE)
        response = self._client.check(client.CheckRequest(repo_root=root))
        if response.problems:
            lines = "\n".join(f"layout: {problem}" for problem in response.problems)
            return cli.CliResponse(1, stdout="", stderr=lines)
        rows, apps = response.counts
        return cli.CliResponse.ok(
            f"layout: {rows} rows, {apps} app trees — disk, declarations, and gates agree"
        )

    def trees(self, req: cli.CliRequest) -> cli.CliResponse:
        root = req.arg(0, "repo-root", _TREES_USAGE)
        req.no_extra_args(1, _TREES_USAGE)
        checked = self._client.check(client.CheckRequest(repo_root=root))
        if checked.problems:
            lines = "\n".join(f"layout: {problem}" for problem in checked.problems)
            return cli.CliResponse(1, stdout="", stderr=lines)
        response = self._client.trees(client.TreesRequest(repo_root=root))
        return cli.CliResponse.ok("\n".join(response.trees))
