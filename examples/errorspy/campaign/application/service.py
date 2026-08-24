from __future__ import annotations

import tesser.application as ts

import campaign.application.ports.campaign_repository as campaign_repository
import campaign.application.views as views
import campaign.client.client as client
import campaign.domain.campaign as campaign
import campaign.domain.short_link as short_link
import campaign.domain.values as values
import tesser.errors as errors


class CampaignService(ts.ApplicationService):

    def __init__(self, repo: campaign_repository.CampaignRepository) -> None:
        self._repo = repo

    def create_campaign(self, req: client.CreateCampaignRequest) -> client.CampaignView:
        window_spec = values.DateWindowSpec(start=req.window_start, end=req.window_end)
        link_specs = tuple(
            short_link.ShortLinkSpec(slug=link.slug, target_url=link.target_url)
            for link in req.links
        )
        spec = campaign.CampaignSpec(id=req.campaign_id, window=window_spec, links=link_specs)
        c = campaign.Campaign(spec)
        window_start = str(c.window.start)
        window_end = str(c.window.end)
        window_record = campaign_repository.WindowRecord(start=window_start, end=window_end)
        link_records: list[campaign_repository.LinkRecord] = []
        for link in c.links:
            link_slug = str(link.slug)
            link_target = str(link.target)
            record = campaign_repository.LinkRecord(slug=link_slug, target_url=link_target)
            link_records.append(record)
        saved_links = tuple(link_records)
        save_campaign_request = campaign_repository.SaveCampaignRequest(
            id=c.id, window=window_record, links=saved_links
        )
        self._repo.save(save_campaign_request)
        view_links = tuple(str(link.slug) for link in c.links)
        return client.CampaignView(campaign_id=c.id, links=view_links)

    def get_campaign(self, req: client.GetCampaignRequest) -> client.CampaignView:
        campaign_id = values.CampaignID(req.campaign_id)
        campaign_id_text = str(campaign_id)
        find_campaign_request = campaign_repository.FindCampaignRequest(
            campaign_id=campaign_id_text
        )
        found = self._repo.find(find_campaign_request)
        campaign_spec_mapper = views.MapToCampaignSpec(
            find_campaign_request=find_campaign_request, found_campaign=found
        )
        found_link_specs = tuple(
            short_link.ShortLinkSpec(
                slug=short_link_spec_mapper.slug,
                target_url=short_link_spec_mapper.target_url,
            )
            for short_link_spec_mapper in campaign_spec_mapper.short_link_spec_mappers
        )
        found_campaign_spec = campaign.CampaignSpec(
            id=campaign_spec_mapper.campaign_id,
            window=values.DateWindowSpec(
                start=campaign_spec_mapper.window_start,
                end=campaign_spec_mapper.window_end,
            ),
            links=found_link_specs,
        )
        try:
            c = campaign.Campaign(found_campaign_spec)
        except errors.DomainError as e:
            raise errors.InfraError(
                f"corrupted campaign record {campaign_spec_mapper.campaign_id!r}: {e}"
            ) from e
        view_links = tuple(str(link.slug) for link in c.links)
        return client.CampaignView(campaign_id=c.id, links=view_links)

    def add_link(self, req: client.AddLinkRequest) -> client.CampaignView:
        errors.collect(
            campaign_id=lambda: values.CampaignID(req.campaign_id),
            slug=lambda: values.Slug(req.slug),
            target_url=lambda: values.TargetURL(req.target_url),
        )
        campaign_id = values.CampaignID(req.campaign_id)
        campaign_id_text = str(campaign_id)
        find_campaign_request = campaign_repository.FindCampaignRequest(
            campaign_id=campaign_id_text
        )
        found = self._repo.find(find_campaign_request)
        campaign_spec_mapper = views.MapToCampaignSpec(
            find_campaign_request=find_campaign_request, found_campaign=found
        )
        found_link_specs = tuple(
            short_link.ShortLinkSpec(
                slug=short_link_spec_mapper.slug,
                target_url=short_link_spec_mapper.target_url,
            )
            for short_link_spec_mapper in campaign_spec_mapper.short_link_spec_mappers
        )
        found_campaign_spec = campaign.CampaignSpec(
            id=campaign_spec_mapper.campaign_id,
            window=values.DateWindowSpec(
                start=campaign_spec_mapper.window_start,
                end=campaign_spec_mapper.window_end,
            ),
            links=found_link_specs,
        )
        try:
            c = campaign.Campaign(found_campaign_spec)
        except errors.DomainError as e:
            raise errors.InfraError(
                f"corrupted campaign record {campaign_spec_mapper.campaign_id!r}: {e}"
            ) from e
        c.add_link(short_link.ShortLinkSpec(slug=req.slug, target_url=req.target_url))
        window_start = str(c.window.start)
        window_end = str(c.window.end)
        window_record = campaign_repository.WindowRecord(start=window_start, end=window_end)
        link_records: list[campaign_repository.LinkRecord] = []
        for link in c.links:
            link_slug = str(link.slug)
            link_target = str(link.target)
            record = campaign_repository.LinkRecord(slug=link_slug, target_url=link_target)
            link_records.append(record)
        saved_links = tuple(link_records)
        save_campaign_request = campaign_repository.SaveCampaignRequest(
            id=c.id, window=window_record, links=saved_links
        )
        self._repo.save(save_campaign_request)
        view_links = tuple(str(link.slug) for link in c.links)
        return client.CampaignView(campaign_id=c.id, links=view_links)

    def deactivate_link(self, req: client.DeactivateLinkRequest) -> client.CampaignView:
        campaign_id = values.CampaignID(req.campaign_id)
        campaign_id_text = str(campaign_id)
        find_campaign_request = campaign_repository.FindCampaignRequest(
            campaign_id=campaign_id_text
        )
        found = self._repo.find(find_campaign_request)
        campaign_spec_mapper = views.MapToCampaignSpec(
            find_campaign_request=find_campaign_request, found_campaign=found
        )
        found_link_specs = tuple(
            short_link.ShortLinkSpec(
                slug=short_link_spec_mapper.slug,
                target_url=short_link_spec_mapper.target_url,
            )
            for short_link_spec_mapper in campaign_spec_mapper.short_link_spec_mappers
        )
        found_campaign_spec = campaign.CampaignSpec(
            id=campaign_spec_mapper.campaign_id,
            window=values.DateWindowSpec(
                start=campaign_spec_mapper.window_start,
                end=campaign_spec_mapper.window_end,
            ),
            links=found_link_specs,
        )
        try:
            c = campaign.Campaign(found_campaign_spec)
        except errors.DomainError as e:
            raise errors.InfraError(
                f"corrupted campaign record {campaign_spec_mapper.campaign_id!r}: {e}"
            ) from e
        c.deactivate_link(values.Slug(req.slug))
        window_start = str(c.window.start)
        window_end = str(c.window.end)
        window_record = campaign_repository.WindowRecord(start=window_start, end=window_end)
        link_records: list[campaign_repository.LinkRecord] = []
        for link in c.links:
            link_slug = str(link.slug)
            link_target = str(link.target)
            record = campaign_repository.LinkRecord(slug=link_slug, target_url=link_target)
            link_records.append(record)
        saved_links = tuple(link_records)
        save_campaign_request = campaign_repository.SaveCampaignRequest(
            id=c.id, window=window_record, links=saved_links
        )
        self._repo.save(save_campaign_request)
        view_links = tuple(str(link.slug) for link in c.links)
        return client.CampaignView(campaign_id=c.id, links=view_links)
