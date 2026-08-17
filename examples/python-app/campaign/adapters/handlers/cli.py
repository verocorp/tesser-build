from __future__ import annotations

from typing import Final

import tesser.adapters as ts

import campaign.client.client as client
from protocol.cli import CliRequest, CliResponse

_CREATE_USAGE: Final[str] = "usage: create-campaign <budget_amount> <currency>"
_ADD_USAGE: Final[str] = "usage: add-link <campaign_id> <slug> <target_url>"
_DEACTIVATE_USAGE: Final[str] = "usage: deactivate-link <campaign_id> <slug>"


class Handler(ts.Handler):
    def __init__(self, client: client.Client) -> None:
        self._client = client

    def create_campaign(self, req: CliRequest) -> CliResponse:
        amount = req.arg(0, "budget_amount", _CREATE_USAGE)
        currency = req.arg(1, "currency", _CREATE_USAGE)
        req.no_extra_args(2, _CREATE_USAGE)
        view = self._client.create_campaign(
            client.CreateCampaignRequest(budget_amount=amount, budget_currency=currency)
        )
        return CliResponse.ok(
            f"created campaign {view.campaign_id} "
            f"with budget {view.budget_amount} {view.budget_currency}"
        )

    def add_link(self, req: CliRequest) -> CliResponse:
        campaign_id = req.arg(0, "campaign_id", _ADD_USAGE)
        slug = req.arg(1, "slug", _ADD_USAGE)
        target_url = req.arg(2, "target_url", _ADD_USAGE)
        req.no_extra_args(3, _ADD_USAGE)
        view = self._client.add_link(
            client.AddLinkRequest(campaign_id=campaign_id, slug=slug, target_url=target_url)
        )
        return CliResponse.ok(f"campaign {view.campaign_id} now has {len(view.links)} link(s)")

    def deactivate_link(self, req: CliRequest) -> CliResponse:
        campaign_id = req.arg(0, "campaign_id", _DEACTIVATE_USAGE)
        slug = req.arg(1, "slug", _DEACTIVATE_USAGE)
        req.no_extra_args(2, _DEACTIVATE_USAGE)
        view = self._client.deactivate_link(
            client.DeactivateLinkRequest(campaign_id=campaign_id, slug=slug)
        )
        active = sum(1 for link in view.links if link.status == "active")
        return CliResponse.ok(f"campaign {view.campaign_id} now has {active} active link(s)")
