from __future__ import annotations

import tesser.adapters as ts

import campaign.application.ports.campaign_queries as campaign_queries
import campaign.application.ports.campaign_repository as campaign_repository
from tesser.errors import InfraError


class InMemoryCampaignRepository(ts.Repository):

    def __init__(self, *, down: bool = False) -> None:
        self._rows: dict[str, campaign_repository.CampaignRecord] = {}
        self._down = down
        self.close_count = 0

    def save(
        self, request: campaign_repository.SaveCampaignRequest
    ) -> campaign_repository.SaveCampaignResponse:
        if self._down:
            raise InfraError("campaign store unavailable")
        self._rows[request.id] = campaign_repository.CampaignRecord(
            id=request.id, budget=request.budget, links=request.links
        )
        return campaign_repository.SaveCampaignResponse()

    def find_view(
        self, request: campaign_queries.FindCampaignViewRequest
    ) -> campaign_queries.FindCampaignViewResponse:
        if self._down:
            raise InfraError("campaign store unavailable")
        row = self._rows.get(request.campaign_id)
        if row is None:
            return campaign_queries.FindCampaignViewResponse(
                outcome=campaign_queries.CampaignViewLookup.MISSING, campaigns=()
            )
        links: list[campaign_queries.LinkViewRow] = []
        for link in row.links:
            links.append(campaign_queries.LinkViewRow(
                slug=link.slug,
                target_url=link.target_url,
                status=link.status,
            ))
        view = campaign_queries.CampaignViewRow(
            campaign_id=row.id,
            budget_amount=row.budget.amount,
            budget_currency=row.budget.currency,
            links=tuple(links),
        )
        return campaign_queries.FindCampaignViewResponse(
            outcome=campaign_queries.CampaignViewLookup.FOUND, campaigns=(view,)
        )

    def find(
        self, request: campaign_repository.FindCampaignRequest
    ) -> campaign_repository.FindCampaignResponse:
        if self._down:
            raise InfraError("campaign store unavailable")
        row = self._rows.get(request.campaign_id)
        if row is None:
            return campaign_repository.FindCampaignResponse(
                outcome=campaign_repository.CampaignLookup.MISSING, campaigns=()
            )
        return campaign_repository.FindCampaignResponse(
            outcome=campaign_repository.CampaignLookup.FOUND, campaigns=(row,)
        )

    def find_by_slug(
        self, request: campaign_repository.FindCampaignBySlugRequest
    ) -> campaign_repository.FindCampaignResponse:
        if self._down:
            raise InfraError("campaign store unavailable")
        for row in self._rows.values():
            if any(link.slug == request.slug for link in row.links):
                return campaign_repository.FindCampaignResponse(
                    outcome=campaign_repository.CampaignLookup.FOUND, campaigns=(row,)
                )
        return campaign_repository.FindCampaignResponse(
            outcome=campaign_repository.CampaignLookup.MISSING, campaigns=()
        )

    def slug_taken(
        self, request: campaign_repository.SlugTakenRequest
    ) -> campaign_repository.SlugTakenResponse:
        if self._down:
            raise InfraError("campaign store unavailable")
        taken = any(link.slug == request.slug for row in self._rows.values() for link in row.links)
        return campaign_repository.SlugTakenResponse(
            availability=campaign_repository.SlugAvailability.TAKEN
            if taken
            else campaign_repository.SlugAvailability.FREE
        )

    def all(
        self, request: campaign_repository.ListCampaignsRequest
    ) -> campaign_repository.ListCampaignsResponse:
        if self._down:
            raise InfraError("campaign store unavailable")
        return campaign_repository.ListCampaignsResponse(campaigns=tuple(self._rows.values()))

    def close(self) -> None:
        self.close_count += 1
