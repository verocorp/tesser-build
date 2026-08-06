from __future__ import annotations

import tesser.adapters as ts

from campaign.application.parts import CampaignParts, FoundCampaign, MissingCampaign
from errors import InfraError


class InMemoryCampaignRepository(ts.Repository):

    def __init__(self, *, down: bool = False) -> None:
        self._rows: dict[str, CampaignParts] = {}
        self._down = down
        self.close_count = 0

    def save(self, parts: CampaignParts) -> None:
        if self._down:
            raise InfraError("campaign store unavailable")
        self._rows[parts.id] = parts

    def find(self, id: str) -> FoundCampaign | MissingCampaign:
        if self._down:
            raise InfraError("campaign store unavailable")
        row = self._rows.get(id)
        return MissingCampaign() if row is None else FoundCampaign(parts=row)

    def find_by_slug(self, slug: str) -> FoundCampaign | MissingCampaign:
        if self._down:
            raise InfraError("campaign store unavailable")
        for row in self._rows.values():
            if any(link.slug == slug for link in row.links):
                return FoundCampaign(parts=row)
        return MissingCampaign()

    def slug_taken(self, slug: str) -> bool:
        if self._down:
            raise InfraError("campaign store unavailable")
        return any(link.slug == slug for row in self._rows.values() for link in row.links)

    def all(self) -> tuple[CampaignParts, ...]:
        if self._down:
            raise InfraError("campaign store unavailable")
        return tuple(self._rows.values())

    def close(self) -> None:
        self.close_count += 1
