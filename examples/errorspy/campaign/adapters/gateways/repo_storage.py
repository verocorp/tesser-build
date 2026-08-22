from __future__ import annotations

import tesser.adapters as ts

import campaign.application.ports.campaign_repository as campaign_repository
from tesser.errors import InfraError
from storage import FakeStorage, Record, StorageMiss, StorageUnavailable


class StorageCampaignRepository(ts.Repository):

    def __init__(self, storage: FakeStorage) -> None:
        self._storage = storage

    def save(
        self, request: campaign_repository.SaveCampaignRequest
    ) -> campaign_repository.SaveCampaignResponse:
        self._storage.put(request.id, _to_record(request))
        return campaign_repository.SaveCampaignResponse()

    def find(
        self, request: campaign_repository.FindCampaignRequest
    ) -> campaign_repository.FindCampaignResponse:
        try:
            row = self._storage.load(request.campaign_id)
        except StorageMiss:
            return campaign_repository.FindCampaignResponse(
                outcome=campaign_repository.CampaignLookup.MISSING, campaigns=()
            )
        except StorageUnavailable as e:
            raise InfraError(
                f"storage unavailable loading campaign {request.campaign_id!r}"
            ) from e
        return campaign_repository.FindCampaignResponse(
            outcome=campaign_repository.CampaignLookup.FOUND,
            campaigns=(_from_record(request.campaign_id, row),),
        )


@ts.do_not_use_function
def _to_record(request: campaign_repository.SaveCampaignRequest) -> Record:  # tesser:debt TB051
    return {
        "window": {"start": request.window.start, "end": request.window.end},
        "links": [
            {"slug": link.slug, "target_url": link.target_url}
            for link in request.links
        ],
    }


@ts.do_not_use_function
def _from_record(campaign_id: str, row: Record) -> campaign_repository.CampaignRecord:  # tesser:debt TB051
    return campaign_repository.CampaignRecord(
        id=campaign_id,
        window=campaign_repository.WindowRecord(
            start=row["window"]["start"], end=row["window"]["end"]
        ),
        links=tuple(
            campaign_repository.LinkRecord(slug=link["slug"], target_url=link["target_url"])
            for link in row["links"]
        ),
    )
