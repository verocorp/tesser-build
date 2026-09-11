from __future__ import annotations

import sys
import typing

import tesser.srv as ts

import app as app
import campaign.adapters.handlers as handlers
import protocol as protocol

_USAGE: typing.Final[str] = (
    "usage: python -m srv.cli.main <command> [args]\n"
    "commands:\n"
    "  create-campaign <budget_amount> <currency>\n"
    "  add-link <campaign_id> <slug> <target_url>\n"
    "  deactivate-link <campaign_id> <slug>"
)


class CliHost(ts.Host):

    def run(self, argv: list[str]) -> int:
        python_app = app.load()
        try:
            cli_handler = handlers.CliHandler(python_app.campaign.client)
            commands: dict[str, protocol.Command] = {
                "create-campaign": cli_handler.create_campaign,
                "add-link": cli_handler.add_link,
                "deactivate-link": cli_handler.deactivate_link,
            }
            if not argv or argv[0] not in commands:
                cli_response = protocol.CliResponse(2, stdout="", stderr=_USAGE)
            else:
                try:
                    cli_response = commands[argv[0]](protocol.CliRequest(args=tuple(argv[1:])))
                except protocol.UsageError as e:
                    cli_response = protocol.CliResponse(2, stdout="", stderr=str(e))
                except Exception:
                    cli_response = protocol.CliResponse(1, stdout="", stderr="unexpected error")
            if cli_response.stdout:
                print(cli_response.stdout)  # noqa: T201
            if cli_response.stderr:
                print(cli_response.stderr, file=sys.stderr)  # noqa: T201
            return cli_response.exit_code
        finally:
            python_app.close()


if __name__ == "__main__":
    ts.main(CliHost().run)
