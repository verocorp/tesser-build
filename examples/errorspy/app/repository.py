from __future__ import annotations

from typing import Protocol

from app.storage import FakeStorage, Record, StorageMiss, StorageUnavailable
from domain.campaign import Campaign, CampaignSpec
from domain.short_link import ShortLinkSpec
from domain.values import DateWindowSpec
from errors import DomainError, InfraError, not_found


class CampaignRepository(Protocol):
    def get(self, campaign_id: str) -> Campaign: ...
    def save(self, campaign: Campaign) -> None: ...


class StorageCampaignRepository:

    def __init__(self, storage: FakeStorage) -> None:
        self._storage = storage

    def save(self, campaign: Campaign) -> None:
        self._storage.put(campaign.id, _to_record(campaign))

    def get(self, campaign_id: str) -> Campaign:
        try:
            record = self._storage.load(campaign_id)
        except StorageMiss as e:
            raise not_found(
                "campaign_missing", f"no campaign {campaign_id!r}"
            ) from e
        except StorageUnavailable as e:
            raise InfraError(
                f"storage unavailable loading campaign {campaign_id!r}"
            ) from e
        try:
            return _reconstruct(campaign_id, record)
        except DomainError as e:
            raise InfraError(
                f"corrupted campaign record {campaign_id!r}: {e}"
            ) from e


def _to_record(campaign: Campaign) -> Record:
    return {
        "window": {
            "start": str(campaign.window.start),
            "end": str(campaign.window.end),
        },
        "links": [
            {"slug": str(link.slug), "target_url": str(link.target)}
            for link in campaign.links
        ],
    }


def _reconstruct(campaign_id: str, record: Record) -> Campaign:
    window = record["window"]
    spec = CampaignSpec(
        window=DateWindowSpec(start=window["start"], end=window["end"]),
        links=tuple(
            ShortLinkSpec(slug=link["slug"], target_url=link["target_url"])
            for link in record["links"]
        ),
    )
    return Campaign(campaign_id, spec)
