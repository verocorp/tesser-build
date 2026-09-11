from __future__ import annotations

import tesser.adapters as ts

import campaign.application.ports as ports
import tesser.errors as errors  # tesser:debt TB050
import storage


class StorageCampaignRepository(ts.Repository):

    def __init__(self, backend: storage.FakeStorage) -> None:
        self._backend = backend

    def save(
        self, save_campaign_request: ports.SaveCampaignRequest
    ) -> ports.SaveCampaignResponse:
        record: storage.Record = {
            "window": {
                "start": save_campaign_request.window.start,
                "end": save_campaign_request.window.end,
            },
            "links": [
                {"slug": link.slug, "target_url": link.target_url}
                for link in save_campaign_request.links
            ],
        }
        self._backend.put(save_campaign_request.id, record)
        return ports.SaveCampaignResponse()

    def find(
        self, find_campaign_request: ports.FindCampaignRequest
    ) -> ports.FindCampaignResponse:
        try:
            row = self._backend.load(find_campaign_request.campaign_id)
        except storage.StorageMiss:
            return ports.FindCampaignResponse(
                outcome=ports.CampaignLookup.MISSING, campaigns=()
            )
        except storage.StorageUnavailable as e:
            raise errors.InfraError(
                f"storage unavailable loading campaign {find_campaign_request.campaign_id!r}"
            ) from e
        campaign_record = ports.CampaignRecord(
            id=find_campaign_request.campaign_id,
            window=ports.WindowRecord(
                start=row["window"]["start"], end=row["window"]["end"]
            ),
            links=tuple(
                ports.LinkRecord(slug=link["slug"], target_url=link["target_url"])
                for link in row["links"]
            ),
        )
        return ports.FindCampaignResponse(
            outcome=ports.CampaignLookup.FOUND,
            campaigns=(campaign_record,),
        )
