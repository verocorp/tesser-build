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
        find_campaign_by_slug_request: ports.FindCampaignBySlugRequest,
        find_campaign_response: ports.FindCampaignResponse,
    ) -> None:
        match find_campaign_response.outcome:
            case ports.CampaignLookup.FOUND:
                record = find_campaign_response.campaigns[0]
            case ports.CampaignLookup.MISSING:
                raise errors.not_found(
                    "link_missing",
                    f"no active link for slug {find_campaign_by_slug_request.slug!r}",
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


class MapToLinkView(ts.Mapper, client.LinkView):

    def __init__(self, link_view_row: ports.LinkViewRow) -> None:
        super().__init__(
            slug=link_view_row.slug,
            target_url=link_view_row.target_url,
            status=link_view_row.status,
        )


class MapToCampaignView(ts.Mapper, client.CampaignView):

    def __init__(
        self,
        find_campaign_view_request: ports.FindCampaignViewRequest,
        find_campaign_view_response: ports.FindCampaignViewResponse,
    ) -> None:
        match find_campaign_view_response.outcome:
            case ports.CampaignViewLookup.FOUND:
                row = find_campaign_view_response.campaigns[0]
            case ports.CampaignViewLookup.MISSING:
                raise errors.not_found(
                    "campaign_missing",
                    f"no campaign with id {find_campaign_view_request.campaign_id!r}",
                )
            case _ as unreachable:
                typing.assert_never(unreachable)
        super().__init__(
            campaign_id=row.campaign_id,
            budget_amount=row.budget_amount,
            budget_currency=row.budget_currency,
            links=tuple(MapToLinkView(link_view_row=link) for link in row.links),
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
        match check_target_response.verdict:
            case ports.PolicyVerdict.ALLOWED:
                pass
            case ports.PolicyVerdict.BLOCKED:
                raise errors.conflict(
                    "destination_blocked",
                    f"destination not allowed: {check_target_response.reason}",
                )
            case _ as unreachable:
                typing.assert_never(unreachable)
        match slug_taken_response.availability:
            case ports.SlugAvailability.FREE:
                pass
            case ports.SlugAvailability.TAKEN:
                raise errors.conflict(
                    "duplicate_slug", f"slug {add_link_request.slug!r} already exists"
                )
            case _ as unreachable_availability:
                typing.assert_never(unreachable_availability)
        super().__init__(
            slug=add_link_request.slug, target_url=add_link_request.target_url, active=True
        )


class MapToCampaignSpecFromRecord(ts.Mapper, domain.CampaignSpec):

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
                    f"no campaign with id {find_campaign_request.campaign_id!r}",
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
    ) -> client.CampaignView:
        issue_campaign_identity_response = self._campaign_identity.issue(
            ports.IssueCampaignIdentityRequest()
        )
        campaign = domain.Campaign(MapToCampaignSpec(
            create_campaign_request=create_campaign_request,
            issue_campaign_identity_response=issue_campaign_identity_response,
            short_links_spec=domain.ShortLinksSpec(links=()),
        ))
        save_campaign_request = MapToSaveCampaignRequest(campaign=campaign)
        self._campaign_repository.save(save_campaign_request)
        find_campaign_view_request = ports.FindCampaignViewRequest(
            campaign_id=save_campaign_request.id,
        )
        find_campaign_view_response = self._campaign_queries.find_view(
            find_campaign_view_request
        )
        return MapToCampaignView(
            find_campaign_view_request=find_campaign_view_request,
            find_campaign_view_response=find_campaign_view_response,
        )

    def add_link(self, add_link_request: client.AddLinkRequest) -> client.CampaignView:
        slug = domain.Slug(add_link_request.slug)
        target_url = domain.TargetURL(add_link_request.target_url)
        campaign_id = domain.CampaignID(add_link_request.campaign_id)
        campaign_id_text = str(campaign_id)
        check_target_response = self._target_policy.check(
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
        find_campaign_request = ports.FindCampaignRequest(campaign_id=campaign_id_text)
        find_campaign_response = self._campaign_repository.find(find_campaign_request)
        campaign = domain.Campaign(MapToCampaignSpecFromRecord(
            find_campaign_request=find_campaign_request,
            find_campaign_response=find_campaign_response,
        ))
        campaign.add_short_link(short_link_spec)
        self._campaign_repository.save(MapToSaveCampaignRequest(campaign=campaign))
        find_campaign_view_request = ports.FindCampaignViewRequest(
            campaign_id=campaign_id_text,
        )
        find_campaign_view_response = self._campaign_queries.find_view(
            find_campaign_view_request
        )
        return MapToCampaignView(
            find_campaign_view_request=find_campaign_view_request,
            find_campaign_view_response=find_campaign_view_response,
        )

    def deactivate_link(
        self, deactivate_link_request: client.DeactivateLinkRequest
    ) -> client.CampaignView:
        campaign_id = domain.CampaignID(deactivate_link_request.campaign_id)
        campaign_id_text = str(campaign_id)
        find_campaign_request = ports.FindCampaignRequest(campaign_id=campaign_id_text)
        find_campaign_response = self._campaign_repository.find(find_campaign_request)
        campaign = domain.Campaign(MapToCampaignSpecFromRecord(
            find_campaign_request=find_campaign_request,
            find_campaign_response=find_campaign_response,
        ))
        slug = domain.Slug(deactivate_link_request.slug)
        campaign.deactivate_short_link(slug)
        self._campaign_repository.save(MapToSaveCampaignRequest(campaign=campaign))
        find_campaign_view_request = ports.FindCampaignViewRequest(
            campaign_id=campaign_id_text,
        )
        find_campaign_view_response = self._campaign_queries.find_view(
            find_campaign_view_request
        )
        return MapToCampaignView(
            find_campaign_view_request=find_campaign_view_request,
            find_campaign_view_response=find_campaign_view_response,
        )

    def get_campaign(
        self, get_campaign_request: client.GetCampaignRequest
    ) -> client.CampaignView:
        campaign_id = domain.CampaignID(get_campaign_request.campaign_id)
        campaign_id_text = str(campaign_id)
        find_campaign_view_request = ports.FindCampaignViewRequest(
            campaign_id=campaign_id_text,
        )
        find_campaign_view_response = self._campaign_queries.find_view(
            find_campaign_view_request
        )
        return MapToCampaignView(
            find_campaign_view_request=find_campaign_view_request,
            find_campaign_view_response=find_campaign_view_response,
        )

    def resolve(self, resolve_request: client.ResolveRequest) -> client.ResolveResponse:
        slug = domain.Slug(resolve_request.slug)
        slug_text = str(slug)
        find_campaign_by_slug_request = ports.FindCampaignBySlugRequest(slug=slug_text)
        find_campaign_response = self._campaign_repository.find_by_slug(
            find_campaign_by_slug_request
        )
        campaign = domain.Campaign(MapToCampaignSpecFromSlugLookup(
            find_campaign_by_slug_request=find_campaign_by_slug_request,
            find_campaign_response=find_campaign_response,
        ))
        target_url = campaign.active_target(slug)
        target_url_text = str(target_url)
        return client.ResolveResponse(target_url=target_url_text)

    def list_links(
        self, list_links_request: client.ListLinksRequest
    ) -> client.ListLinksResponse:
        list_campaigns_response = self._campaign_repository.all(
            ports.ListCampaignsRequest()
        )
        views: list[client.LinkView] = []
        for listed_campaign in list_campaigns_response.campaigns:
            for link in listed_campaign.links:
                link_view = client.LinkView(
                    slug=link.slug, target_url=link.target_url, status=link.status
                )
                views.append(link_view)
        listed_views = tuple(views)
        return client.ListLinksResponse(links=listed_views)
