from __future__ import annotations

import functools
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
            case ports.FindCampaignOutcome.FOUND:
                record = find_campaign_response.campaigns[0]
            case ports.FindCampaignOutcome.NOT_FOUND:
                raise client.CampaignNotFound(
                    message=f"no campaign {find_campaign_request.campaign_id!r}"
                )
            case _ as unreachable:
                typing.assert_never(unreachable)
        super().__init__(
            id=record.id,
            window=domain.DateWindowSpec(start=record.window.start, end=record.window.end),
            links=tuple(MapToShortLinkSpec(link) for link in record.links),
        )


class MapToShortLinkSpecFromLinkBody(ts.Mapper, domain.ShortLinkSpec):

    def __init__(self, link_body: client.LinkBody) -> None:
        super().__init__(slug=link_body.slug, target_url=link_body.target_url)


class MapToCampaignSpecFromCreateRequest(ts.Mapper, domain.CampaignSpec):

    def __init__(self, create_campaign_request: client.CreateCampaignRequest) -> None:
        super().__init__(
            id=create_campaign_request.campaign_id,
            window=domain.DateWindowSpec(
                start=create_campaign_request.window_start,
                end=create_campaign_request.window_end,
            ),
            links=tuple(
                MapToShortLinkSpecFromLinkBody(link_body)
                for link_body in create_campaign_request.links
            ),
        )


class MapToRejection(ts.Mapper, client.Rejection):

    def __init__(self, domain_error: errors.DomainError) -> None:
        super().__init__(
            code=domain_error.code,
            message=domain_error.message,
            field=domain_error.field or "",
            problems=tuple(
                client.Problem(
                    code=problem.code,
                    field=problem.field or "",
                    message=problem.message,
                )
                for problem in domain_error.problems
            ),
        )


class MapToFindCampaignRequest(ts.Mapper, ports.FindCampaignRequest):

    def __init__(self, campaign_id: domain.CampaignID) -> None:
        super().__init__(campaign_id=str(campaign_id))


class MapToWindowRecord(ts.Mapper, ports.WindowRecord):

    def __init__(self, campaign: domain.Campaign) -> None:
        super().__init__(start=str(campaign.window.start), end=str(campaign.window.end))


class MapToLinkRecord(ts.Mapper, ports.LinkRecord):

    def __init__(self, short_link: domain.ShortLink) -> None:
        super().__init__(slug=str(short_link.slug), target_url=str(short_link.target))


class MapToSaveCampaignRequest(ts.Mapper, ports.SaveCampaignRequest):

    def __init__(self, campaign: domain.Campaign) -> None:
        super().__init__(
            id=campaign.id,
            window=MapToWindowRecord(campaign),
            links=tuple(MapToLinkRecord(link) for link in campaign.links),
        )


class MapToCampaign(ts.Mapper, client.Campaign):

    def __init__(self, campaign: domain.Campaign) -> None:
        super().__init__(
            campaign_id=campaign.id,
            links=tuple(str(link.slug) for link in campaign.links),
        )


class MapToCreateCampaignResponse(ts.Mapper, client.CreateCampaignResponse):

    def __init__(self, campaign: client.Campaign) -> None:
        super().__init__(campaign=campaign)


class MapToGetCampaignResponse(ts.Mapper, client.GetCampaignResponse):

    def __init__(self, campaign: client.Campaign) -> None:
        super().__init__(campaign=campaign)


class MapToAddLinkResponse(ts.Mapper, client.AddLinkResponse):

    def __init__(self, campaign: client.Campaign) -> None:
        super().__init__(campaign=campaign)


class MapToDeactivateLinkResponse(ts.Mapper, client.DeactivateLinkResponse):

    def __init__(self, campaign: client.Campaign) -> None:
        super().__init__(campaign=campaign)


class CampaignService(ts.ApplicationService):

    def __init__(self, campaign_repository: ports.CampaignRepository) -> None:
        self._campaign_repository = campaign_repository

    def create_campaign(
        self, create_campaign_request: client.CreateCampaignRequest
    ) -> client.CreateCampaignResponse:
        campaign_spec = MapToCampaignSpecFromCreateRequest(create_campaign_request)
        try:
            campaign = domain.Campaign(campaign_spec)
        except errors.DomainError as domain_error:
            rejection = MapToRejection(domain_error)
            raise client.CampaignRejected(rejection) from domain_error
        self._campaign_repository.save_campaign(MapToSaveCampaignRequest(campaign))
        return MapToCreateCampaignResponse(MapToCampaign(campaign))

    def get_campaign(
        self, get_campaign_request: client.GetCampaignRequest
    ) -> client.GetCampaignResponse:
        try:
            campaign_id = domain.CampaignID(get_campaign_request.campaign_id)
        except errors.DomainError as domain_error:
            rejection = MapToRejection(domain_error)
            raise client.CampaignRejected(rejection) from domain_error
        find_campaign_request = MapToFindCampaignRequest(campaign_id)
        find_campaign_response = self._campaign_repository.find_campaign(find_campaign_request)
        campaign_spec = MapToCampaignSpec(
            find_campaign_request=find_campaign_request,
            find_campaign_response=find_campaign_response,
        )
        campaign = domain.Campaign(campaign_spec)
        return MapToGetCampaignResponse(MapToCampaign(campaign))

    def add_link(self, add_link_request: client.AddLinkRequest) -> client.AddLinkResponse:
        validate_campaign_id = functools.partial(domain.CampaignID, add_link_request.campaign_id)
        validate_slug = functools.partial(domain.Slug, add_link_request.slug)
        validate_target_url = functools.partial(domain.TargetURL, add_link_request.target_url)
        try:
            errors.collect(
                campaign_id=validate_campaign_id,
                slug=validate_slug,
                target_url=validate_target_url,
            )
            campaign_id = domain.CampaignID(add_link_request.campaign_id)
        except errors.DomainError as domain_error:
            rejection = MapToRejection(domain_error)
            raise client.CampaignRejected(rejection) from domain_error
        find_campaign_request = MapToFindCampaignRequest(campaign_id)
        find_campaign_response = self._campaign_repository.find_campaign(find_campaign_request)
        campaign_spec = MapToCampaignSpec(
            find_campaign_request=find_campaign_request,
            find_campaign_response=find_campaign_response,
        )
        campaign = domain.Campaign(campaign_spec)
        try:
            campaign.add_link(
                domain.ShortLinkSpec(
                    slug=add_link_request.slug, target_url=add_link_request.target_url
                )
            )
        except errors.DomainError as domain_error:
            raise client.LinkNotAdded(
                code=domain_error.code, message=domain_error.message
            ) from domain_error
        self._campaign_repository.save_campaign(MapToSaveCampaignRequest(campaign))
        return MapToAddLinkResponse(MapToCampaign(campaign))

    def deactivate_link(
        self, deactivate_link_request: client.DeactivateLinkRequest
    ) -> client.DeactivateLinkResponse:
        try:
            campaign_id = domain.CampaignID(deactivate_link_request.campaign_id)
        except errors.DomainError as domain_error:
            rejection = MapToRejection(domain_error)
            raise client.CampaignRejected(rejection) from domain_error
        find_campaign_request = MapToFindCampaignRequest(campaign_id)
        find_campaign_response = self._campaign_repository.find_campaign(find_campaign_request)
        campaign_spec = MapToCampaignSpec(
            find_campaign_request=find_campaign_request,
            find_campaign_response=find_campaign_response,
        )
        campaign = domain.Campaign(campaign_spec)
        try:
            slug = domain.Slug(deactivate_link_request.slug)
        except errors.DomainError as domain_error:
            rejection = MapToRejection(domain_error)
            raise client.CampaignRejected(rejection) from domain_error
        try:
            campaign.deactivate_link(slug)
        except errors.DomainError as domain_error:
            raise client.LinkNotDeactivated(
                code=domain_error.code, message=domain_error.message
            ) from domain_error
        self._campaign_repository.save_campaign(MapToSaveCampaignRequest(campaign))
        return MapToDeactivateLinkResponse(MapToCampaign(campaign))
