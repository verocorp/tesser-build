from __future__ import annotations

import asyncio
import sys
import traceback
import typing

import tesser.srv as ts

import alpha.adapters.handlers as alpha_handlers
import app as app
import protocol as protocol

_USAGE: typing.Final[str] = "usage: add <name> <part> | create <name> | approve <name> | find <name>"


class CliHost(ts.Host):

    def run(self, argv: list[str]) -> int:
        try:
            minimal_app = app.load()
            try:
                handler = alpha_handlers.Handler(minimal_app.alpha.client)
                try:
                    cli_request = protocol.CliRequest(args=tuple(argv[1:]))
                    match argv[:1]:
                        case ["add"]:
                            cli_response = asyncio.run(handler.add_part(cli_request))
                        case ["create"]:
                            cli_response = asyncio.run(handler.create_widget(cli_request))
                        case ["approve"]:
                            cli_response = asyncio.run(handler.approve_widget(cli_request))
                        case ["find"]:
                            cli_response = asyncio.run(handler.find_widget(cli_request))
                        case _:
                            raise protocol.UsageError(_USAGE)
                except protocol.UsageError as e:
                    cli_response = protocol.CliResponse(exit_code=2, line=protocol.Line(text=str(e)))
                sys.stdout.write(cli_response.line.text + "\n")
                return cli_response.exit_code
            finally:
                minimal_app.close()
        except Exception:
            traceback.print_exc(file=sys.stderr)
            sys.stdout.write("unexpected error\n")
            return 1


if __name__ == "__main__":
    ts.main(CliHost().run)
