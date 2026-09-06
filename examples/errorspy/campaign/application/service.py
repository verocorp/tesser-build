from __future__ import annotations

import typing

import tesser.application as ts

import campaign.application.ports as ports
import campaign.client as client
import campaign.domain as domain
import tesser.errors as errors


class MapToShortLinkSpec(ts.Mapper, domain.ShortLinkSpec):

    def __init__(self, link_record: ports.LinkRecord) -> None:
        super().__init__(slug=link_record.slug, target_url=link_record.target_url)


class MapToCampaignSpec(ts.Mapper, domain.CampaignSpec):

    def __init__(
        self,
        find_campaign_request: ports.FindCampaignRequest,
        find_campaign_response: ports.FindCampaignResponse,
    ) -> None:
        match find_campaign_response.outcome:
            case ports.CampaignLookup.FOUND:
                record = find_campaign_response.campaigns[0]
            case ports.CampaignLookup.MISSING:
                raise errors.not_found(
                    "campaign_missing",
                    f"no campaign {find_campaign_request.campaign_id!r}",
                )
            case _ as unreachable:
                typing.assert_never(unreachable)
        super().__init__(
            id=record.id,
            window=domain.DateWindowSpec(start=record.window.start, end=record.window.end),
            links=tuple(MapToShortLinkSpec(link) for link in record.links),
        )


class CampaignService(ts.ApplicationService):

    def __init__(self, campaign_repository: ports.CampaignRepository) -> None:
        self._campaign_repository = campaign_repository

    def create_campaign(
        self, create_campaign_request: client.CreateCampaignRequest
    ) -> client.CampaignView:
        date_window_spec = domain.DateWindowSpec(
            start=create_campaign_request.window_start,
            end=create_campaign_request.window_end,
        )
        link_specs = tuple(
            domain.ShortLinkSpec(slug=link.slug, target_url=link.target_url)
            for link in create_campaign_request.links
        )
        campaign_spec = domain.CampaignSpec(
            id=create_campaign_request.campaign_id, window=date_window_spec, links=link_specs
        )
        campaign = domain.Campaign(campaign_spec)
        window_start = str(campaign.window.start)
        window_end = str(campaign.window.end)
        window_record = ports.WindowRecord(start=window_start, end=window_end)
        link_records: list[ports.LinkRecord] = []
        for link in campaign.links:
            link_slug = str(link.slug)
            link_target = str(link.target)
            link_record = ports.LinkRecord(slug=link_slug, target_url=link_target)
            link_records.append(link_record)
        saved_links = tuple(link_records)
        save_campaign_request = ports.SaveCampaignRequest(
            id=campaign.id, window=window_record, links=saved_links
        )
        self._campaign_repository.save(save_campaign_request)
        view_links = tuple(str(link.slug) for link in campaign.links)
        return client.CampaignView(campaign_id=campaign.id, links=view_links)

    def get_campaign(
        self, get_campaign_request: client.GetCampaignRequest
    ) -> client.CampaignView:
        campaign_id = domain.CampaignID(get_campaign_request.campaign_id)
        campaign_id_text = str(campaign_id)
        find_campaign_request = ports.FindCampaignRequest(campaign_id=campaign_id_text)
        find_campaign_response = self._campaign_repository.find(find_campaign_request)
        campaign_spec = MapToCampaignSpec(
            find_campaign_request=find_campaign_request,
            find_campaign_response=find_campaign_response,
        )
        try:
            campaign = domain.Campaign(campaign_spec)
        except errors.DomainError as e:
            raise errors.InfraError(
                f"corrupted campaign record {campaign_id_text!r}: {e}"
            ) from e
        view_links = tuple(str(link.slug) for link in campaign.links)
        return client.CampaignView(campaign_id=campaign.id, links=view_links)

    def add_link(self, add_link_request: client.AddLinkRequest) -> client.CampaignView:
        errors.collect(
            campaign_id=lambda: domain.CampaignID(add_link_request.campaign_id),
            slug=lambda: domain.Slug(add_link_request.slug),
            target_url=lambda: domain.TargetURL(add_link_request.target_url),
        )
        campaign_id = domain.CampaignID(add_link_request.campaign_id)
        campaign_id_text = str(campaign_id)
        find_campaign_request = ports.FindCampaignRequest(campaign_id=campaign_id_text)
        find_campaign_response = self._campaign_repository.find(find_campaign_request)
        campaign_spec = MapToCampaignSpec(
            find_campaign_request=find_campaign_request,
            find_campaign_response=find_campaign_response,
        )
        try:
            campaign = domain.Campaign(campaign_spec)
        except errors.DomainError as e:
            raise errors.InfraError(
                f"corrupted campaign record {campaign_id_text!r}: {e}"
            ) from e
        campaign.add_link(
            domain.ShortLinkSpec(
                slug=add_link_request.slug, target_url=add_link_request.target_url
            )
        )
        window_start = str(campaign.window.start)
        window_end = str(campaign.window.end)
        window_record = ports.WindowRecord(start=window_start, end=window_end)
        link_records: list[ports.LinkRecord] = []
        for link in campaign.links:
            link_slug = str(link.slug)
            link_target = str(link.target)
            link_record = ports.LinkRecord(slug=link_slug, target_url=link_target)
            link_records.append(link_record)
        saved_links = tuple(link_records)
        save_campaign_request = ports.SaveCampaignRequest(
            id=campaign.id, window=window_record, links=saved_links
        )
        self._campaign_repository.save(save_campaign_request)
        view_links = tuple(str(link.slug) for link in campaign.links)
        return client.CampaignView(campaign_id=campaign.id, links=view_links)

    def deactivate_link(
        self, deactivate_link_request: client.DeactivateLinkRequest
    ) -> client.CampaignView:
        campaign_id = domain.CampaignID(deactivate_link_request.campaign_id)
        campaign_id_text = str(campaign_id)
        find_campaign_request = ports.FindCampaignRequest(campaign_id=campaign_id_text)
        find_campaign_response = self._campaign_repository.find(find_campaign_request)
        campaign_spec = MapToCampaignSpec(
            find_campaign_request=find_campaign_request,
            find_campaign_response=find_campaign_response,
        )
        try:
            campaign = domain.Campaign(campaign_spec)
        except errors.DomainError as e:
            raise errors.InfraError(
                f"corrupted campaign record {campaign_id_text!r}: {e}"
            ) from e
        campaign.deactivate_link(domain.Slug(deactivate_link_request.slug))
        window_start = str(campaign.window.start)
        window_end = str(campaign.window.end)
        window_record = ports.WindowRecord(start=window_start, end=window_end)
        link_records: list[ports.LinkRecord] = []
        for link in campaign.links:
            link_slug = str(link.slug)
            link_target = str(link.target)
            link_record = ports.LinkRecord(slug=link_slug, target_url=link_target)
            link_records.append(link_record)
        saved_links = tuple(link_records)
        save_campaign_request = ports.SaveCampaignRequest(
            id=campaign.id, window=window_record, links=saved_links
        )
        self._campaign_repository.save(save_campaign_request)
        view_links = tuple(str(link.slug) for link in campaign.links)
        return client.CampaignView(campaign_id=campaign.id, links=view_links)
