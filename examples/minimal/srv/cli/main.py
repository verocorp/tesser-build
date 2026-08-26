from __future__ import annotations

import sys
import typing

import tesser.srv as ts

import alpha.adapters.handlers.cli as cli
import app.loader as loader
import protocol.cli as protocol_cli
import tesser.errors as errors

_USAGE: typing.Final[str] = "usage: add <id> <name> <count> | get <id>"


class CliHost(ts.Host):

    def run(self, argv: list[str]) -> int:
        built = loader.load()
        try:
            handler = cli.Handler(built.alpha.client)
            commands: dict[str, protocol_cli.Command] = {"add": handler.add, "get": handler.get}
            if not argv or argv[0] not in commands:
                response = protocol_cli.CliResponse(exit_code=2, line=protocol_cli.Line(text=_USAGE))
            else:
                try:
                    response = commands[argv[0]](protocol_cli.CliRequest(args=tuple(argv[1:])))
                except protocol_cli.UsageError as e:
                    response = protocol_cli.CliResponse(exit_code=2, line=protocol_cli.Line(text=str(e)))
                except errors.DomainError as e:
                    response = protocol_cli.CliResponse(
                        exit_code=errors.exit_code_for(e.kind), line=protocol_cli.Line(text=e.message)
                    )
                except errors.InfraError:
                    response = protocol_cli.CliResponse(exit_code=1, line=protocol_cli.Line(text="unavailable"))
            sys.stdout.write(response.line.text + "\n")
            return response.exit_code
        finally:
            built.close()


if __name__ == "__main__":
    ts.main(CliHost().run)
