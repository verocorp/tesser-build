from __future__ import annotations

import sys
from collections.abc import Callable
from typing import Final

import tesser.srv as ts

from bootstrap.app import App
from bootstrap.loader import load
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


@ts.do_not_use_function
def commands_for(app: App) -> dict[str, Command]:
    campaign = cli.Handler(app.campaign.client)
    return {
        "create-campaign": campaign.create_campaign,
        "add-link": campaign.add_link,
        "deactivate-link": campaign.deactivate_link,
    }


@ts.do_not_use_function
def respond(run: Callable[[], CliResponse]) -> CliResponse:
    try:
        return run()
    except UsageError as e:
        return CliResponse(2, stdout="", stderr=str(e))
    except DomainError as e:
        return CliResponse(exit_code_for(e.kind), stdout="", stderr=f"[{e.code}] {e.message}")
    except InfraError:
        return CliResponse(1, stdout="", stderr="a dependency is unavailable; please retry")
    except Exception:
        return CliResponse(1, stdout="", stderr="unexpected error")


@ts.do_not_use_function
def dispatch(commands: dict[str, Command], argv: list[str]) -> CliResponse:
    if not argv or argv[0] not in commands:
        return CliResponse(2, stdout="", stderr=_USAGE)
    return respond(lambda: commands[argv[0]](CliRequest(args=tuple(argv[1:]))))


@ts.do_not_use_function
def run(argv: list[str]) -> int:
    app = load()
    try:
        resp = dispatch(commands_for(app), argv)
        if resp.stdout:
            print(resp.stdout)  # noqa: T201
        if resp.stderr:
            print(resp.stderr, file=sys.stderr)  # noqa: T201
        return resp.exit_code
    finally:
        app.close()


if __name__ == "__main__":  # tessercheck:ignore TB051
    raise SystemExit(run(sys.argv[1:]))
