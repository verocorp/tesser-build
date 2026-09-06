from __future__ import annotations

import typing

import tesser.adapters as ts

import protocol
import repo.client as client

_CHECK_USAGE: typing.Final[str] = "usage: python -m srv.cli.check <repo-root>"

_TREES_USAGE: typing.Final[str] = "usage: python -m srv.cli.trees <repo-root>"


class Handler(ts.Handler):

    def __init__(self, repo_client: client.RepoClient) -> None:
        self._repo_client = repo_client

    def check(self, cli_request: protocol.CliRequest) -> protocol.CliResponse:
        root = cli_request.arg(0, "repo-root", _CHECK_USAGE)
        cli_request.no_extra_args(1, _CHECK_USAGE)
        check_response = self._repo_client.check(client.CheckRequest(repo_root=root))
        if check_response.problems:
            lines = "\n".join(f"layout: {problem}" for problem in check_response.problems)
            return protocol.CliResponse(1, stdout="", stderr=lines)
        rows, apps = check_response.counts
        return protocol.CliResponse.ok(
            f"layout: {rows} rows, {apps} app trees — disk, declarations, and gates agree"
        )

    def trees(self, cli_request: protocol.CliRequest) -> protocol.CliResponse:
        root = cli_request.arg(0, "repo-root", _TREES_USAGE)
        cli_request.no_extra_args(1, _TREES_USAGE)
        check_response = self._repo_client.check(client.CheckRequest(repo_root=root))
        if check_response.problems:
            lines = "\n".join(f"layout: {problem}" for problem in check_response.problems)
            return protocol.CliResponse(1, stdout="", stderr=lines)
        trees_response = self._repo_client.trees(client.TreesRequest(repo_root=root))
        return protocol.CliResponse.ok("\n".join(trees_response.trees))
