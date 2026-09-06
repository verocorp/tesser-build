from __future__ import annotations

import sys

import tesser.srv as ts

import alpha.adapters.handlers as handlers
import app as app
import protocol as protocol
import tesser.errors as errors


class CliHost(ts.Host):

    def run(self, argv: list[str]) -> int:
        minimal_app = app.load()
        try:
            handler = handlers.Handler(minimal_app.alpha.client)
            try:
                cli_response = handler.add(protocol.CliRequest(args=tuple(argv)))
            except protocol.UsageError as e:
                cli_response = protocol.CliResponse(exit_code=2, line=protocol.Line(text=str(e)))
            except errors.DomainError as e:
                cli_response = protocol.CliResponse(
                    exit_code=errors.exit_code_for(e.kind), line=protocol.Line(text=e.message)
                )
            except errors.InfraError:
                cli_response = protocol.CliResponse(exit_code=1, line=protocol.Line(text="unavailable"))
            sys.stdout.write(cli_response.line.text + "\n")
            return cli_response.exit_code
        finally:
            minimal_app.close()


if __name__ == "__main__":
    ts.main(CliHost().run)
