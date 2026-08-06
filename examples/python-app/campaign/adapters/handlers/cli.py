from __future__ import annotations

from typing import Final

import tesser.adapters as ts

from campaign.client import AddLinkRequest, Client, CreateCampaignRequest, DeactivateLinkRequest
from cliwire import CliRequest, CliResponse, arg, no_extra_args, ok, respond

_CREATE_USAGE: Final[str] = "usage: create-campaign <budget_amount> <currency>"
_ADD_USAGE: Final[str] = "usage: add-link <campaign_id> <slug> <target_url>"
_DEACTIVATE_USAGE: Final[str] = "usage: deactivate-link <campaign_id> <slug>"


class Handler(ts.Handler):
    def __init__(self, client: Client) -> None:
        self._client = client

    def create_campaign(self, req: CliRequest) -> CliResponse:
        def run() -> CliResponse:
            amount = arg(req, 0, "budget_amount", _CREATE_USAGE)
            currency = arg(req, 1, "currency", _CREATE_USAGE)
            no_extra_args(req, 2, _CREATE_USAGE)
            view = self._client.create_campaign(
                CreateCampaignRequest(budget_amount=amount, budget_currency=currency)
            )
            return ok(
                f"created campaign {view.campaign_id} "
                f"with budget {view.budget_amount} {view.budget_currency}"
            )

        return respond(run)

    def add_link(self, req: CliRequest) -> CliResponse:
        def run() -> CliResponse:
            campaign_id = arg(req, 0, "campaign_id", _ADD_USAGE)
            slug = arg(req, 1, "slug", _ADD_USAGE)
            target_url = arg(req, 2, "target_url", _ADD_USAGE)
            no_extra_args(req, 3, _ADD_USAGE)
            view = self._client.add_link(
                AddLinkRequest(campaign_id=campaign_id, slug=slug, target_url=target_url)
            )
            return ok(f"campaign {view.campaign_id} now has {len(view.links)} link(s)")

        return respond(run)

    def deactivate_link(self, req: CliRequest) -> CliResponse:
        def run() -> CliResponse:
            campaign_id = arg(req, 0, "campaign_id", _DEACTIVATE_USAGE)
            slug = arg(req, 1, "slug", _DEACTIVATE_USAGE)
            no_extra_args(req, 2, _DEACTIVATE_USAGE)
            view = self._client.deactivate_link(
                DeactivateLinkRequest(campaign_id=campaign_id, slug=slug)
            )
            active = sum(1 for link in view.links if link.active)
            return ok(f"campaign {view.campaign_id} now has {active} active link(s)")

        return respond(run)
