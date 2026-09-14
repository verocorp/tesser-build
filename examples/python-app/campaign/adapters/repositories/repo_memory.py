from __future__ import annotations

import tesser.adapters as ts

import campaign.application.ports as ports


class InMemoryCampaignRepository(ts.Repository):

    def __init__(self) -> None:
        self._rows: dict[str, ports.CampaignRecord] = {}
        self.close_count = 0

    def save_campaign(
        self, save_campaign_request: ports.SaveCampaignRequest
    ) -> ports.SaveCampaignResponse:
        self._rows[save_campaign_request.id] = ports.CampaignRecord(
            id=save_campaign_request.id, budget=save_campaign_request.budget, links=save_campaign_request.links
        )
        return ports.SaveCampaignResponse()

    def find_campaign(
        self, find_campaign_request: ports.FindCampaignRequest
    ) -> ports.FindCampaignResponse:
        row = self._rows.get(find_campaign_request.campaign_id)
        if row is None:
            return ports.FindCampaignResponse(
                outcome=ports.FindCampaignOutcome.NOT_FOUND, campaigns=()
            )
        links: list[ports.Link] = []
        for link in row.links:
            links.append(ports.Link(
                slug=link.slug,
                target_url=link.target_url,
                status=link.status,
            ))
        campaign = ports.Campaign(
            campaign_id=row.id,
            budget_amount=row.budget.amount,
            budget_currency=row.budget.currency,
            links=tuple(links),
        )
        return ports.FindCampaignResponse(
            outcome=ports.FindCampaignOutcome.FOUND, campaigns=(campaign,)
        )

    def load_campaign(
        self, load_campaign_request: ports.LoadCampaignRequest
    ) -> ports.LoadCampaignResponse:
        row = self._rows.get(load_campaign_request.campaign_id)
        if row is None:
            return ports.LoadCampaignResponse(
                outcome=ports.LoadCampaignOutcome.NOT_FOUND, campaigns=()
            )
        return ports.LoadCampaignResponse(
            outcome=ports.LoadCampaignOutcome.FOUND, campaigns=(row,)
        )

    def load_campaign_by_slug(
        self, load_campaign_by_slug_request: ports.LoadCampaignBySlugRequest
    ) -> ports.LoadCampaignBySlugResponse:
        for row in self._rows.values():
            if any(link.slug == load_campaign_by_slug_request.slug for link in row.links):
                return ports.LoadCampaignBySlugResponse(
                    outcome=ports.LoadCampaignBySlugOutcome.FOUND, campaigns=(row,)
                )
        return ports.LoadCampaignBySlugResponse(
            outcome=ports.LoadCampaignBySlugOutcome.NOT_FOUND, campaigns=()
        )

    def slug_taken(
        self, slug_taken_request: ports.SlugTakenRequest
    ) -> ports.SlugTakenResponse:
        taken = any(link.slug == slug_taken_request.slug for row in self._rows.values() for link in row.links)
        return ports.SlugTakenResponse(
            outcome=ports.SlugTakenOutcome.TAKEN
            if taken
            else ports.SlugTakenOutcome.FREE
        )

    def list_campaigns(
        self, list_campaigns_request: ports.ListCampaignsRequest
    ) -> ports.ListCampaignsResponse:
        return ports.ListCampaignsResponse(campaigns=tuple(self._rows.values()))

    def close(self) -> None:
        self.close_count += 1
