from __future__ import annotations

import tesser.adapters as ts

import campaign.application.ports as ports
import tesser.errors as errors  # tesser:debt TB050


class InMemoryCampaignRepository(ts.Repository):

    def __init__(self, *, down: bool = False) -> None:
        self._rows: dict[str, ports.CampaignRecord] = {}
        self._down = down
        self.close_count = 0

    def save(
        self, save_campaign_request: ports.SaveCampaignRequest
    ) -> ports.SaveCampaignResponse:
        if self._down:
            raise errors.InfraError("campaign store unavailable")
        self._rows[save_campaign_request.id] = ports.CampaignRecord(
            id=save_campaign_request.id, budget=save_campaign_request.budget, links=save_campaign_request.links
        )
        return ports.SaveCampaignResponse()

    def find_view(
        self, find_campaign_view_request: ports.FindCampaignViewRequest
    ) -> ports.FindCampaignViewResponse:
        if self._down:
            raise errors.InfraError("campaign store unavailable")
        row = self._rows.get(find_campaign_view_request.campaign_id)
        if row is None:
            return ports.FindCampaignViewResponse(
                outcome=ports.CampaignViewLookup.MISSING, campaigns=()
            )
        links: list[ports.LinkViewRow] = []
        for link in row.links:
            links.append(ports.LinkViewRow(
                slug=link.slug,
                target_url=link.target_url,
                status=link.status,
            ))
        campaign_view_row = ports.CampaignViewRow(
            campaign_id=row.id,
            budget_amount=row.budget.amount,
            budget_currency=row.budget.currency,
            links=tuple(links),
        )
        return ports.FindCampaignViewResponse(
            outcome=ports.CampaignViewLookup.FOUND, campaigns=(campaign_view_row,)
        )

    def find(
        self, find_campaign_request: ports.FindCampaignRequest
    ) -> ports.FindCampaignResponse:
        if self._down:
            raise errors.InfraError("campaign store unavailable")
        row = self._rows.get(find_campaign_request.campaign_id)
        if row is None:
            return ports.FindCampaignResponse(
                outcome=ports.CampaignLookup.MISSING, campaigns=()
            )
        return ports.FindCampaignResponse(
            outcome=ports.CampaignLookup.FOUND, campaigns=(row,)
        )

    def find_by_slug(
        self, find_campaign_by_slug_request: ports.FindCampaignBySlugRequest
    ) -> ports.FindCampaignResponse:
        if self._down:
            raise errors.InfraError("campaign store unavailable")
        for row in self._rows.values():
            if any(link.slug == find_campaign_by_slug_request.slug for link in row.links):
                return ports.FindCampaignResponse(
                    outcome=ports.CampaignLookup.FOUND, campaigns=(row,)
                )
        return ports.FindCampaignResponse(
            outcome=ports.CampaignLookup.MISSING, campaigns=()
        )

    def slug_taken(
        self, slug_taken_request: ports.SlugTakenRequest
    ) -> ports.SlugTakenResponse:
        if self._down:
            raise errors.InfraError("campaign store unavailable")
        taken = any(link.slug == slug_taken_request.slug for row in self._rows.values() for link in row.links)
        return ports.SlugTakenResponse(
            availability=ports.SlugAvailability.TAKEN
            if taken
            else ports.SlugAvailability.FREE
        )

    def all(
        self, list_campaigns_request: ports.ListCampaignsRequest
    ) -> ports.ListCampaignsResponse:
        if self._down:
            raise errors.InfraError("campaign store unavailable")
        return ports.ListCampaignsResponse(campaigns=tuple(self._rows.values()))

    def close(self) -> None:
        self.close_count += 1
