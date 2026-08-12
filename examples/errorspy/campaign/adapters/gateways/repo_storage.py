from __future__ import annotations

import tesser.adapters as ts

import campaign.application.parts as parts
from errors import InfraError
from storage import FakeStorage, Record, StorageMiss, StorageUnavailable


class StorageCampaignRepository(ts.Repository):

    def __init__(self, storage: FakeStorage) -> None:
        self._storage = storage

    def save(self, record: parts.CampaignParts) -> None:
        self._storage.put(record.id, _to_record(record))

    def find(self, campaign_id: str) -> parts.FoundCampaign | parts.MissingCampaign:
        try:
            row = self._storage.load(campaign_id)
        except StorageMiss:
            return parts.MissingCampaign()
        except StorageUnavailable as e:
            raise InfraError(
                f"storage unavailable loading campaign {campaign_id!r}"
            ) from e
        return parts.FoundCampaign(parts=_from_record(campaign_id, row))


@ts.function
def _to_record(record: parts.CampaignParts) -> Record:
    return {
        "window": {"start": record.window.start, "end": record.window.end},
        "links": [
            {"slug": link.slug, "target_url": link.target_url}
            for link in record.links
        ],
    }


@ts.function
def _from_record(campaign_id: str, row: Record) -> parts.CampaignParts:
    return parts.CampaignParts(
        id=campaign_id,
        window=parts.WindowParts(start=row["window"]["start"], end=row["window"]["end"]),
        links=tuple(
            parts.LinkParts(slug=link["slug"], target_url=link["target_url"])
            for link in row["links"]
        ),
    )
