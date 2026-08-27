from __future__ import annotations

import asyncio
import sys

import tesser.srv as ts

import app.loader as loader
import ordering.adapters.handlers.cli as cli
import protocol.cli as protocol_cli
import tesser.errors as errors


class CliHost(ts.Host):

    def run(self, argv: list[str]) -> int:
        built = loader.load()
        try:
            handler = cli.Handler(built.ordering.client)

            async def place() -> protocol_cli.CliResponse:
                try:
                    return await handler.place(protocol_cli.CliRequest(args=tuple(argv)))
                except protocol_cli.UsageError as e:
                    return protocol_cli.CliResponse(exit_code=2, line=protocol_cli.Line(text=str(e)))
                except errors.DomainError as e:
                    return protocol_cli.CliResponse(
                        exit_code=errors.exit_code_for(e.kind), line=protocol_cli.Line(text=e.message)
                    )
                except errors.InfraError:
                    return protocol_cli.CliResponse(exit_code=1, line=protocol_cli.Line(text="unavailable"))

            response = asyncio.run(place())
            sys.stdout.write(response.line.text + "\n")
            return response.exit_code
        finally:
            built.close()


if __name__ == "__main__":
    ts.main(CliHost().run)
