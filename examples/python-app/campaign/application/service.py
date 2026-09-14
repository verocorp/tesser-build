from __future__ import annotations

import typing

import tesser.application as ts

import campaign.application.ports as ports
import campaign.client as client
import campaign.domain as domain
import tesser.errors as errors


class MapToShortLinkSpecFromRecord(ts.Mapper, domain.ShortLinkSpec):

    def __init__(self, link_record: ports.LinkRecord) -> None:
        super().__init__(
            slug=link_record.slug,
            target_url=link_record.target_url,
            active=link_record.status == domain.LinkState.ACTIVE.value,
        )


class MapToCampaignSpecFromSlugLookup(ts.Mapper, domain.CampaignSpec):

    def __init__(
        self,
        load_campaign_by_slug_request: ports.LoadCampaignBySlugRequest,
        load_campaign_by_slug_response: ports.LoadCampaignBySlugResponse,
    ) -> None:
        match load_campaign_by_slug_response.outcome:
            case ports.LoadCampaignBySlugOutcome.FOUND:
                record = load_campaign_by_slug_response.campaigns[0]
            case ports.LoadCampaignBySlugOutcome.NOT_FOUND:
                raise client.LinkNotFound(
                    message=f"no active link for slug {load_campaign_by_slug_request.slug!r}",
                )
            case _ as unreachable:
                typing.assert_never(unreachable)
        super().__init__(
            id=record.id,
            budget=domain.MoneySpec(
                amount=record.budget.amount, currency=record.budget.currency
            ),
            links=domain.ShortLinksSpec(links=tuple(
                MapToShortLinkSpecFromRecord(link_record=link_record)
                for link_record in record.links
            )),
        )


class MapToMoneySpec(ts.Mapper, domain.MoneySpec):

    def __init__(self, create_campaign_request: client.CreateCampaignRequest) -> None:
        super().__init__(
            amount=create_campaign_request.budget_amount,
            currency=create_campaign_request.budget_currency,
        )


class MapToCampaignSpec(ts.Mapper, domain.CampaignSpec):

    def __init__(
        self,
        create_campaign_request: client.CreateCampaignRequest,
        issue_campaign_identity_response: ports.IssueCampaignIdentityResponse,
        short_links_spec: domain.ShortLinksSpec,
    ) -> None:
        super().__init__(
            id=issue_campaign_identity_response.campaign_id,
            budget=MapToMoneySpec(create_campaign_request=create_campaign_request),
            links=short_links_spec,
        )


class MapToMoneyRecord(ts.Mapper, ports.MoneyRecord):

    def __init__(self, campaign: domain.Campaign) -> None:
        super().__init__(
            amount=str(campaign.budget.amount),
            currency=str(campaign.budget.currency),
        )


class MapToLinkRecord(ts.Mapper, ports.LinkRecord):

    def __init__(self, short_link: domain.ShortLink) -> None:
        super().__init__(
            slug=str(short_link.slug),
            target_url=str(short_link.target_url),
            status=str(short_link.status),
        )


class MapToSaveCampaignRequest(ts.Mapper, ports.SaveCampaignRequest):

    def __init__(self, campaign: domain.Campaign) -> None:
        super().__init__(
            id=str(campaign.id),
            budget=MapToMoneyRecord(campaign=campaign),
            links=tuple(MapToLinkRecord(short_link=link) for link in campaign.links),
        )


class MapToLink(ts.Mapper, client.Link):

    def __init__(self, link: ports.Link) -> None:
        super().__init__(
            slug=link.slug,
            target_url=link.target_url,
            status=link.status,
        )


class MapToCampaign(ts.Mapper, client.Campaign):

    def __init__(
        self,
        find_campaign_request: ports.FindCampaignRequest,
        find_campaign_response: ports.FindCampaignResponse,
    ) -> None:
        match find_campaign_response.outcome:
            case ports.FindCampaignOutcome.FOUND:
                campaign = find_campaign_response.campaigns[0]
            case ports.FindCampaignOutcome.NOT_FOUND:
                raise client.CampaignNotFound(
                    message=f"no campaign with id {find_campaign_request.campaign_id!r}",
                )
            case _ as unreachable:
                typing.assert_never(unreachable)
        super().__init__(
            campaign_id=campaign.campaign_id,
            budget_amount=campaign.budget_amount,
            budget_currency=campaign.budget_currency,
            links=tuple(MapToLink(link=link) for link in campaign.links),
        )


class MapToCheckTargetRequest(ts.Mapper, ports.CheckTargetRequest):

    def __init__(self, target_url: domain.TargetURL) -> None:
        super().__init__(target_url=str(target_url))


class MapToSlugTakenRequest(ts.Mapper, ports.SlugTakenRequest):

    def __init__(self, slug: domain.Slug) -> None:
        super().__init__(slug=str(slug))


class MapToShortLinkSpec(ts.Mapper, domain.ShortLinkSpec):

    def __init__(
        self,
        add_link_request: client.AddLinkRequest,
        check_target_response: ports.CheckTargetResponse,
        slug_taken_response: ports.SlugTakenResponse,
    ) -> None:
        match check_target_response.outcome:
            case ports.CheckTargetOutcome.ALLOWED:
                pass
            case ports.CheckTargetOutcome.BLOCKED:
                raise client.TargetBlocked(
                    message=f"destination not allowed: {check_target_response.reason}",
                )
            case _ as unreachable:
                typing.assert_never(unreachable)
        match slug_taken_response.outcome:
            case ports.SlugTakenOutcome.FREE:
                pass
            case ports.SlugTakenOutcome.TAKEN:
                raise client.SlugTaken(
                    message=f"slug {add_link_request.slug!r} already exists",
                )
            case _ as unreachable_availability:
                typing.assert_never(unreachable_availability)
        super().__init__(
            slug=add_link_request.slug, target_url=add_link_request.target_url, active=True
        )


class MapToCampaignSpecFromRecord(ts.Mapper, domain.CampaignSpec):

    def __init__(
        self,
        load_campaign_request: ports.LoadCampaignRequest,
        load_campaign_response: ports.LoadCampaignResponse,
    ) -> None:
        match load_campaign_response.outcome:
            case ports.LoadCampaignOutcome.FOUND:
                record = load_campaign_response.campaigns[0]
            case ports.LoadCampaignOutcome.NOT_FOUND:
                raise client.CampaignNotFound(
                    message=f"no campaign with id {load_campaign_request.campaign_id!r}",
                )
            case _ as unreachable:
                typing.assert_never(unreachable)
        super().__init__(
            id=record.id,
            budget=domain.MoneySpec(
                amount=record.budget.amount, currency=record.budget.currency
            ),
            links=domain.ShortLinksSpec(links=tuple(
                MapToShortLinkSpecFromRecord(link_record=link_record)
                for link_record in record.links
            )),
        )


class MapToLoadCampaignRequest(ts.Mapper, ports.LoadCampaignRequest):

    def __init__(self, campaign_id: domain.CampaignID) -> None:
        super().__init__(campaign_id=str(campaign_id))


class MapToFindCampaignRequest(ts.Mapper, ports.FindCampaignRequest):

    def __init__(self, campaign_id: domain.CampaignID) -> None:
        super().__init__(campaign_id=str(campaign_id))


class MapToLoadCampaignBySlugRequest(ts.Mapper, ports.LoadCampaignBySlugRequest):

    def __init__(self, slug: domain.Slug) -> None:
        super().__init__(slug=str(slug))


class MapToResolveSlugResponse(ts.Mapper, client.ResolveSlugResponse):

    def __init__(self, target_url: domain.TargetURL) -> None:
        super().__init__(target_url=str(target_url))


class MapToLinkFromRecord(ts.Mapper, client.Link):

    def __init__(self, link_record: ports.LinkRecord) -> None:
        super().__init__(
            slug=link_record.slug, target_url=link_record.target_url, status=link_record.status
        )


class MapToListLinksResponse(ts.Mapper, client.ListLinksResponse):

    def __init__(self, list_campaigns_response: ports.ListCampaignsResponse) -> None:
        super().__init__(
            links=tuple(
                MapToLinkFromRecord(link_record=link_record)
                for campaign_record in list_campaigns_response.campaigns
                for link_record in campaign_record.links
            )
        )


class MapToCreateCampaignResponse(ts.Mapper, client.CreateCampaignResponse):

    def __init__(self, campaign: client.Campaign) -> None:
        super().__init__(campaign=campaign)


class MapToAddLinkResponse(ts.Mapper, client.AddLinkResponse):

    def __init__(self, campaign: client.Campaign) -> None:
        super().__init__(campaign=campaign)


class MapToDeactivateLinkResponse(ts.Mapper, client.DeactivateLinkResponse):

    def __init__(self, campaign: client.Campaign) -> None:
        super().__init__(campaign=campaign)


class MapToGetCampaignResponse(ts.Mapper, client.GetCampaignResponse):

    def __init__(self, campaign: client.Campaign) -> None:
        super().__init__(campaign=campaign)


class CampaignService(ts.ApplicationService):

    def __init__(
        self,
        campaign_repository: ports.CampaignRepository,
        target_policy: ports.TargetPolicy,
        campaign_identity: ports.CampaignIdentity,
        campaign_queries: ports.CampaignQueries,
    ) -> None:
        self._campaign_repository = campaign_repository
        self._target_policy = target_policy
        self._campaign_identity = campaign_identity
        self._campaign_queries = campaign_queries

    def create_campaign(
        self, create_campaign_request: client.CreateCampaignRequest
    ) -> client.CreateCampaignResponse:
        issue_campaign_identity_response = self._campaign_identity.issue_campaign_identity(
            ports.IssueCampaignIdentityRequest()
        )
        try:
            campaign = domain.Campaign(MapToCampaignSpec(
                create_campaign_request=create_campaign_request,
                issue_campaign_identity_response=issue_campaign_identity_response,
                short_links_spec=domain.ShortLinksSpec(links=()),
            ))
        except errors.DomainError as domain_error:
            raise client.CampaignRejected(
                code=domain_error.code, message=domain_error.message
            ) from domain_error
        save_campaign_request = MapToSaveCampaignRequest(campaign=campaign)
        find_campaign_request = ports.FindCampaignRequest(
            campaign_id=save_campaign_request.id,
        )
        self._campaign_repository.save_campaign(save_campaign_request)
        find_campaign_response = self._campaign_queries.find_campaign(find_campaign_request)
        return MapToCreateCampaignResponse(
            MapToCampaign(
                find_campaign_request=find_campaign_request,
                find_campaign_response=find_campaign_response,
            )
        )

    def add_link(self, add_link_request: client.AddLinkRequest) -> client.AddLinkResponse:
        try:
            slug = domain.Slug(add_link_request.slug)
            target_url = domain.TargetURL(add_link_request.target_url)
            campaign_id = domain.CampaignID(add_link_request.campaign_id)
        except errors.DomainError as domain_error:
            raise client.CampaignRejected(
                code=domain_error.code, message=domain_error.message
            ) from domain_error
        check_target_response = self._target_policy.check_target(
            MapToCheckTargetRequest(target_url=target_url)
        )
        slug_taken_response = self._campaign_repository.slug_taken(
            MapToSlugTakenRequest(slug=slug)
        )
        short_link_spec = MapToShortLinkSpec(
            add_link_request=add_link_request,
            check_target_response=check_target_response,
            slug_taken_response=slug_taken_response,
        )
        load_campaign_request = MapToLoadCampaignRequest(campaign_id=campaign_id)
        load_campaign_response = self._campaign_repository.load_campaign(load_campaign_request)
        campaign = domain.Campaign(MapToCampaignSpecFromRecord(
            load_campaign_request=load_campaign_request,
            load_campaign_response=load_campaign_response,
        ))
        try:
            campaign.add_short_link(short_link_spec)
        except errors.DomainError as domain_error:
            raise client.SlugTaken(message=domain_error.message) from domain_error
        find_campaign_request = MapToFindCampaignRequest(campaign_id=campaign_id)
        self._campaign_repository.save_campaign(MapToSaveCampaignRequest(campaign=campaign))
        find_campaign_response = self._campaign_queries.find_campaign(find_campaign_request)
        return MapToAddLinkResponse(
            MapToCampaign(
                find_campaign_request=find_campaign_request,
                find_campaign_response=find_campaign_response,
            )
        )

    def deactivate_link(
        self, deactivate_link_request: client.DeactivateLinkRequest
    ) -> client.DeactivateLinkResponse:
        try:
            campaign_id = domain.CampaignID(deactivate_link_request.campaign_id)
        except errors.DomainError as domain_error:
            raise client.CampaignRejected(
                code=domain_error.code, message=domain_error.message
            ) from domain_error
        load_campaign_request = MapToLoadCampaignRequest(campaign_id=campaign_id)
        load_campaign_response = self._campaign_repository.load_campaign(load_campaign_request)
        campaign = domain.Campaign(MapToCampaignSpecFromRecord(
            load_campaign_request=load_campaign_request,
            load_campaign_response=load_campaign_response,
        ))
        try:
            slug = domain.Slug(deactivate_link_request.slug)
        except errors.DomainError as domain_error:
            raise client.CampaignRejected(
                code=domain_error.code, message=domain_error.message
            ) from domain_error
        try:
            campaign.deactivate_short_link(slug)
        except errors.DomainError as domain_error:
            raise client.LinkNotFound(message=domain_error.message) from domain_error
        find_campaign_request = MapToFindCampaignRequest(campaign_id=campaign_id)
        self._campaign_repository.save_campaign(MapToSaveCampaignRequest(campaign=campaign))
        find_campaign_response = self._campaign_queries.find_campaign(find_campaign_request)
        return MapToDeactivateLinkResponse(
            MapToCampaign(
                find_campaign_request=find_campaign_request,
                find_campaign_response=find_campaign_response,
            )
        )

    def get_campaign(
        self, get_campaign_request: client.GetCampaignRequest
    ) -> client.GetCampaignResponse:
        try:
            campaign_id = domain.CampaignID(get_campaign_request.campaign_id)
        except errors.DomainError as domain_error:
            raise client.CampaignRejected(
                code=domain_error.code, message=domain_error.message
            ) from domain_error
        find_campaign_request = MapToFindCampaignRequest(campaign_id=campaign_id)
        find_campaign_response = self._campaign_queries.find_campaign(find_campaign_request)
        return MapToGetCampaignResponse(
            MapToCampaign(
                find_campaign_request=find_campaign_request,
                find_campaign_response=find_campaign_response,
            )
        )

    def resolve_slug(
        self, resolve_slug_request: client.ResolveSlugRequest
    ) -> client.ResolveSlugResponse:
        try:
            slug = domain.Slug(resolve_slug_request.slug)
        except errors.DomainError as domain_error:
            raise client.CampaignRejected(
                code=domain_error.code, message=domain_error.message
            ) from domain_error
        load_campaign_by_slug_request = MapToLoadCampaignBySlugRequest(slug=slug)
        load_campaign_by_slug_response = self._campaign_repository.load_campaign_by_slug(
            load_campaign_by_slug_request
        )
        campaign = domain.Campaign(MapToCampaignSpecFromSlugLookup(
            load_campaign_by_slug_request=load_campaign_by_slug_request,
            load_campaign_by_slug_response=load_campaign_by_slug_response,
        ))
        try:
            target_url = campaign.active_target(slug)
        except errors.DomainError as domain_error:
            raise client.LinkNotFound(message=domain_error.message) from domain_error
        return MapToResolveSlugResponse(target_url=target_url)

    def list_links(
        self, list_links_request: client.ListLinksRequest
    ) -> client.ListLinksResponse:
        list_campaigns_response = self._campaign_repository.list_campaigns(
            ports.ListCampaignsRequest()
        )
        return MapToListLinksResponse(list_campaigns_response=list_campaigns_response)
