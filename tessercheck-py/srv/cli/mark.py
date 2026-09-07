from __future__ import annotations

import sys
import typing

import tesser.srv as ts

import app
import protocol
import tesser.errors as errors
import tessercheck.adapters.handlers as handlers

_USAGE: typing.Final[str] = "usage: python -m srv.cli.mark [tree]"


class MarkHost(ts.Host):

    def run(self, argv: list[str]) -> int:
        tessercheck_app = app.load()
        try:
            handler = handlers.Handler(tessercheck_app.tessercheck.client)
            try:
                resp = handler.mark(protocol.CliRequest(args=tuple(argv)))
            except protocol.UsageError as e:
                resp = protocol.CliResponse(2, stdout="", stderr=f"{e}\n{_USAGE}")
            except errors.DomainError as e:
                resp = protocol.CliResponse(
                    errors.exit_code_for(e.kind), stdout="", stderr=e.message
                )
            except errors.InfraError:
                resp = protocol.CliResponse(1, stdout="", stderr="unavailable")
            except Exception:
                resp = protocol.CliResponse(1, stdout="", stderr="unexpected error")
            if resp.stdout:
                print(resp.stdout)
            if resp.stderr:
                print(resp.stderr, file=sys.stderr)
            return resp.exit_code
        finally:
            tessercheck_app.close()


if __name__ == "__main__":
    ts.main(MarkHost().run)
