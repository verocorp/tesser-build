from __future__ import annotations

import sys

import tesser.srv as ts

import alpha.adapters.handlers as handlers
import app.loader as loader
import protocol.cli as cli
import tesser.errors as errors


class CliHost(ts.Host):

    def run(self, argv: list[str]) -> int:
        built = loader.load()
        try:
            handler = handlers.Handler(built.alpha.client)
            try:
                cli_response = handler.add(cli.CliRequest(args=tuple(argv)))
            except cli.UsageError as e:
                cli_response = cli.CliResponse(exit_code=2, line=cli.Line(text=str(e)))
            except errors.DomainError as e:
                cli_response = cli.CliResponse(
                    exit_code=errors.exit_code_for(e.kind), line=cli.Line(text=e.message)
                )
            except errors.InfraError:
                cli_response = cli.CliResponse(exit_code=1, line=cli.Line(text="unavailable"))
            sys.stdout.write(cli_response.line.text + "\n")
            return cli_response.exit_code
        finally:
            built.close()


if __name__ == "__main__":
    ts.main(CliHost().run)
