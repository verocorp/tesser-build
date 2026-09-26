from __future__ import annotations

import asyncio
import sys
import traceback

import tesser.srv as ts

import alpha.adapters.handlers as alpha_handlers
import app
import protocol


class CliHost(ts.Host):

    def run(self, argv: list[str]) -> int:
        return asyncio.run(self._serve(argv))

    async def _serve(self, argv: list[str]) -> int:
        asyncpg_app = app.load()
        try:
            await asyncpg_app.open()
            handler = alpha_handlers.Handler(asyncpg_app.alpha.client)
            try:
                cli_response = await handler.add(protocol.CliRequest(args=tuple(argv)))
            except protocol.UsageError as e:
                cli_response = protocol.CliResponse(
                    exit_code=2, line=protocol.Line(text=str(e))
                )
            except Exception:
                traceback.print_exc(file=sys.stderr)
                cli_response = protocol.CliResponse(
                    exit_code=1, line=protocol.Line(text="unexpected error")
                )
            sys.stdout.write(cli_response.line.text + "\n")
            return cli_response.exit_code
        finally:
            await asyncpg_app.close()


if __name__ == "__main__":
    ts.main(CliHost().run)
