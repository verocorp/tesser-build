from __future__ import annotations

import typing

import tesser.adapters as ts

import protocol
import trees.client as client

_GENERATE_USAGE: typing.Final[str] = "usage: python -m srv.cli.generate <spec.toml> <out-dir>"


class Handler(ts.Handler):

    def __init__(self, trees_client: client.TreesClient) -> None:
        self._trees_client = trees_client

    def generate(self, cli_request: protocol.CliRequest) -> protocol.CliResponse:
        spec_path = cli_request.arg(0, "spec.toml", _GENERATE_USAGE)
        out_dir = cli_request.arg(1, "out-dir", _GENERATE_USAGE)
        cli_request.no_extra_args(2, _GENERATE_USAGE)
        generate_tree_response = self._trees_client.generate_tree(
            client.GenerateTreeRequest(spec_path=spec_path, out_dir=out_dir)
        )
        if generate_tree_response.problems:
            lines = "\n".join(f"generate: {problem}" for problem in generate_tree_response.problems)
            return protocol.CliResponse(1, stdout="", stderr=lines)
        return protocol.CliResponse.ok("\n".join(generate_tree_response.paths))
