from __future__ import annotations

import sys

import tesser.srv as ts

import alpha.adapters.handlers.cli as cli
import app.loader as loader
import protocol.cli as protocol_cli
import tesser.errors as errors


class CliHost(ts.Host):

    def run(self, argv: list[str]) -> int:
        built = loader.load()
        try:
            handler = cli.Handler(built.alpha.client)
            try:
                response = handler.add(protocol_cli.CliRequest(args=tuple(argv)))
            except protocol_cli.UsageError as e:
                response = protocol_cli.CliResponse(exit_code=2, line=protocol_cli.Line(text=str(e)))
            except errors.InfraError:
                response = protocol_cli.CliResponse(exit_code=1, line=protocol_cli.Line(text="unavailable"))
            sys.stdout.write(response.line.text + "\n")
            return response.exit_code
        finally:
            built.close()


if __name__ == "__main__":
    ts.main(CliHost().run)
