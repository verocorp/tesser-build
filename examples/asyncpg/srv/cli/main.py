from __future__ import annotations

import asyncio
import sys

import tesser.srv as ts

import alpha.adapters.handlers.cli as cli
import app.loader as loader
import protocol.cli as protocol_cli
import tesser.errors as errors


class CliHost(ts.Host):

    def run(self, argv: list[str]) -> int:
        async def serve() -> int:
            built = loader.load()
            try:
                await built.start()
                handler = cli.Handler(built.alpha.client)
                try:
                    response = await handler.add(protocol_cli.CliRequest(args=tuple(argv)))
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
                await built.close()

        return asyncio.run(serve())


if __name__ == "__main__":
    ts.main(CliHost().run)
