from __future__ import annotations

import sys
import traceback

import tesser.srv as ts

import alpha.adapters.handlers as handlers
import app as app
import protocol as protocol


class CliHost(ts.Host):

    def run(self, argv: list[str]) -> int:
        try:
            minimal_app = app.load()
            try:
                handler = handlers.Handler(minimal_app.alpha.client)
                try:
                    cli_response = handler.add(protocol.CliRequest(args=tuple(argv)))
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
