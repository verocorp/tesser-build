from __future__ import annotations

import os
import sys

from bootstrap.bootstrap import App, new
from bootstrap.config import from_env
from campaign.adapters.handlers.cli import Handler as CampaignHandler
from cliwire import CliRequest, CliResponse, Command

_USAGE = (
    "usage: python -m srv.cli.main <command> [args]\n"
    "commands:\n"
    "  create-campaign <budget_amount> <currency>\n"
    "  add-link <campaign_id> <slug> <target_url>\n"
    "  deactivate-link <campaign_id> <slug>"
)


def commands_for(app: App) -> dict[str, Command]:
    campaign = CampaignHandler(app.campaign)
    return {
        "create-campaign": campaign.create_campaign,
        "add-link": campaign.add_link,
        "deactivate-link": campaign.deactivate_link,
    }


def dispatch(commands: dict[str, Command], argv: list[str]) -> CliResponse:
    if not argv or argv[0] not in commands:
        return CliResponse(2, stderr=_USAGE)
    return commands[argv[0]](CliRequest(args=tuple(argv[1:])))


def run(argv: list[str]) -> int:
    app = new(from_env(os.getenv))
    try:
        resp = dispatch(commands_for(app), argv)
        if resp.stdout:
            print(resp.stdout)  # noqa: T201
        if resp.stderr:
            print(resp.stderr, file=sys.stderr)  # noqa: T201
        return resp.exit_code
    finally:
        app.close()


if __name__ == "__main__":
    raise SystemExit(run(sys.argv[1:]))
