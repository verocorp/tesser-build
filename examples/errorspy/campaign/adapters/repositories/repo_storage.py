from __future__ import annotations

import tesser.adapters as ts

import campaign.application.ports.campaign_repository as campaign_repository
import tesser.errors as errors
import storage


class StorageCampaignRepository(ts.Repository):

    def __init__(self, backend: storage.FakeStorage) -> None:
        self._storage = backend

    def save(
        self, request: campaign_repository.SaveCampaignRequest
    ) -> campaign_repository.SaveCampaignResponse:
        record: storage.Record = {
            "window": {"start": request.window.start, "end": request.window.end},
            "links": [
                {"slug": link.slug, "target_url": link.target_url}
                for link in request.links
            ],
        }
        self._storage.put(request.id, record)
        return campaign_repository.SaveCampaignResponse()

    def find(
        self, request: campaign_repository.FindCampaignRequest
    ) -> campaign_repository.FindCampaignResponse:
        try:
            row = self._storage.load(request.campaign_id)
        except storage.StorageMiss:
            return campaign_repository.FindCampaignResponse(
                outcome=campaign_repository.CampaignLookup.MISSING, campaigns=()
            )
        except storage.StorageUnavailable as e:
            raise errors.InfraError(
                f"storage unavailable loading campaign {request.campaign_id!r}"
            ) from e
        record = campaign_repository.CampaignRecord(
            id=request.campaign_id,
            window=campaign_repository.WindowRecord(
                start=row["window"]["start"], end=row["window"]["end"]
            ),
            links=tuple(
                campaign_repository.LinkRecord(slug=link["slug"], target_url=link["target_url"])
                for link in row["links"]
            ),
        )
        return campaign_repository.FindCampaignResponse(
            outcome=campaign_repository.CampaignLookup.FOUND,
            campaigns=(record,),
        )

