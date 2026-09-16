from __future__ import annotations

import sys

import tesser.srv as ts

import app
import protocol
import trees.adapters.handlers as trees_handlers


class GenerateHost(ts.Host):

    def run(self, argv: list[str]) -> int:
        generator_app = app.load()
        handler = trees_handlers.Handler(generator_app.trees.client)
        try:
            cli_response = handler.generate(protocol.CliRequest(args=tuple(argv)))
        except protocol.UsageError as error:
            cli_response = protocol.CliResponse(2, stdout="", stderr=str(error))
        generator_app.close()
        if cli_response.stdout:
            print(cli_response.stdout)
        if cli_response.stderr:
            print(cli_response.stderr, file=sys.stderr)
        return cli_response.exit_code


if __name__ == "__main__":
    ts.main(GenerateHost().run)
