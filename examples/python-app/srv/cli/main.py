from __future__ import annotations

import sys
from typing import Final

import tesser.srv as ts

from app.loader import load
import campaign.adapters.handlers.cli as cli
from protocol.cli import CliRequest, CliResponse, Command, UsageError
from tesser.errors import DomainError, InfraError, exit_code_for

_USAGE: Final[str] = (
    "usage: python -m srv.cli.main <command> [args]\n"
    "commands:\n"
    "  create-campaign <budget_amount> <currency>\n"
    "  add-link <campaign_id> <slug> <target_url>\n"
    "  deactivate-link <campaign_id> <slug>"
)


class CliHost(ts.Host):

    def run(self, argv: list[str]) -> int:
        app = load()
        try:
            campaign = cli.Handler(app.campaign.client)
            commands: dict[str, Command] = {
                "create-campaign": campaign.create_campaign,
                "add-link": campaign.add_link,
                "deactivate-link": campaign.deactivate_link,
            }
            if not argv or argv[0] not in commands:
                resp = CliResponse(2, stdout="", stderr=_USAGE)
            else:
                try:
                    resp = commands[argv[0]](CliRequest(args=tuple(argv[1:])))
                except UsageError as e:
                    resp = CliResponse(2, stdout="", stderr=str(e))
                except DomainError as e:
                    resp = CliResponse(
                        exit_code_for(e.kind), stdout="", stderr=f"[{e.code}] {e.message}"
                    )
                except InfraError:
                    resp = CliResponse(
                        1, stdout="", stderr="a dependency is unavailable; please retry"
                    )
                except Exception:
                    resp = CliResponse(1, stdout="", stderr="unexpected error")
            if resp.stdout:
                print(resp.stdout)  # noqa: T201
            if resp.stderr:
                print(resp.stderr, file=sys.stderr)  # noqa: T201
            return resp.exit_code
        finally:
            app.close()


if __name__ == "__main__":
    ts.main(CliHost().run)
