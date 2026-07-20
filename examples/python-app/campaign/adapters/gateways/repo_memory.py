from __future__ import annotations

from dataclasses import dataclass

from campaign.application.parts import CampaignParts, campaign_parts
from campaign.domain.campaign import Campaign, CampaignSpec
from campaign.domain.money import MoneySpec
from campaign.domain.short_link import ShortLinkSpec
from campaign.domain.values import CampaignID, Slug
from errors import InfraError


@dataclass(frozen=True)
class _LinkRow:
    slug: str
    target_url: str
    active: bool


@dataclass(frozen=True)
class _CampaignRow:
    campaign_id: str
    budget_amount: str
    budget_currency: str
    links: tuple[_LinkRow, ...]


def _row(parts: CampaignParts) -> _CampaignRow:
    return _CampaignRow(
        campaign_id=parts.id,
        budget_amount=parts.budget.amount,
        budget_currency=parts.budget.currency,
        links=tuple(
            _LinkRow(slug=link.slug, target_url=link.target_url, active=link.active)
            for link in parts.links
        ),
    )


def _spec(row: _CampaignRow) -> CampaignSpec:
    return CampaignSpec(
        id=row.campaign_id,
        budget=MoneySpec(amount=row.budget_amount, currency=row.budget_currency),
        links=tuple(
            ShortLinkSpec(slug=link.slug, target_url=link.target_url, active=link.active)
            for link in row.links
        ),
    )


class InMemoryCampaignRepository:
    def __init__(self, *, down: bool = False) -> None:
        self._rows: dict[str, _CampaignRow] = {}
        self._down = down
        self.close_count = 0

    def save(self, c: Campaign) -> None:
        if self._down:
            raise InfraError("campaign store unavailable")
        parts = campaign_parts(c)
        self._rows[parts.id] = _row(parts)

    def find(self, id: CampaignID) -> Campaign | None:
        if self._down:
            raise InfraError("campaign store unavailable")
        row = self._rows.get(str(id))
        return None if row is None else Campaign(_spec(row))

    def find_by_slug(self, slug: Slug) -> Campaign | None:
        if self._down:
            raise InfraError("campaign store unavailable")
        value = str(slug)
        for row in self._rows.values():
            if any(link.slug == value for link in row.links):
                return Campaign(_spec(row))
        return None

    def all(self) -> tuple[Campaign, ...]:
        if self._down:
            raise InfraError("campaign store unavailable")
        return tuple(Campaign(_spec(row)) for row in self._rows.values())

    def close(self) -> None:
        self.close_count += 1
