from __future__ import annotations

import typing

import tesser.application as ts

import campaign.application.ports.campaign_repository as campaign_repository
import tesser.errors as errors


class MapToShortLinkSpec(ts.Mapper):

    def __init__(self, link_record: campaign_repository.LinkRecord) -> None:
        self._slug = link_record.slug
        self._target_url = link_record.target_url

    @property
    def slug(self) -> str:
        return self._slug

    @property
    def target_url(self) -> str:
        return self._target_url


class MapToCampaignSpec(ts.Mapper):

    def __init__(
        self,
        find_campaign_request: campaign_repository.FindCampaignRequest,
        found_campaign: campaign_repository.FindCampaignResponse,
    ) -> None:
        match found_campaign.outcome:
            case campaign_repository.CampaignLookup.FOUND:
                record = found_campaign.campaigns[0]
            case campaign_repository.CampaignLookup.MISSING:
                raise errors.not_found(
                    "campaign_missing",
                    f"no campaign {find_campaign_request.campaign_id!r}",
                )
            case _ as unreachable:
                typing.assert_never(unreachable)
        self._campaign_id = record.id
        self._window_start = record.window.start
        self._window_end = record.window.end
        self._short_link_spec_mappers = tuple(
            MapToShortLinkSpec(link_record=link) for link in record.links
        )

    @property
    def campaign_id(self) -> str:
        return self._campaign_id

    @property
    def window_start(self) -> str:
        return self._window_start

    @property
    def window_end(self) -> str:
        return self._window_end

    @property
    def short_link_spec_mappers(self) -> tuple[MapToShortLinkSpec, ...]:
        return self._short_link_spec_mappers

