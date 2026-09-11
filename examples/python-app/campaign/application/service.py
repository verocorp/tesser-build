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
                raise client.Missing(
                    code="link_missing",
                    message=f"no active link for slug {find_campaign_by_slug_request.slug!r}",
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
                raise client.Missing(
                    code="campaign_missing",
                    message=f"no campaign with id {find_campaign_view_request.campaign_id!r}",
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
                raise client.Conflict(
                    code="destination_blocked",
                    message=f"destination not allowed: {check_target_response.reason}",
                )
            case _ as unreachable:
                typing.assert_never(unreachable)
        match slug_taken_response.availability:
            case ports.SlugAvailability.FREE:
                pass
            case ports.SlugAvailability.TAKEN:
                raise client.Conflict(
                    code="duplicate_slug",
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
        find_campaign_request: ports.FindCampaignRequest,
        find_campaign_response: ports.FindCampaignResponse,
    ) -> None:
        match find_campaign_response.outcome:
            case ports.CampaignLookup.FOUND:
                record = find_campaign_response.campaigns[0]
            case ports.CampaignLookup.MISSING:
                raise client.Missing(
                    code="campaign_missing",
                    message=f"no campaign with id {find_campaign_request.campaign_id!r}",
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


class MapToFindCampaignRequest(ts.Mapper, ports.FindCampaignRequest):

    def __init__(self, campaign_id: domain.CampaignID) -> None:
        super().__init__(campaign_id=str(campaign_id))


class MapToFindCampaignViewRequest(ts.Mapper, ports.FindCampaignViewRequest):

    def __init__(self, campaign_id: domain.CampaignID) -> None:
        super().__init__(campaign_id=str(campaign_id))


class MapToFindCampaignBySlugRequest(ts.Mapper, ports.FindCampaignBySlugRequest):

    def __init__(self, slug: domain.Slug) -> None:
        super().__init__(slug=str(slug))


class MapToResolveResponse(ts.Mapper, client.ResolveResponse):

    def __init__(self, target_url: domain.TargetURL) -> None:
        super().__init__(target_url=str(target_url))


class MapToLinkViewFromRecord(ts.Mapper, client.LinkView):

    def __init__(self, link_record: ports.LinkRecord) -> None:
        super().__init__(
            slug=link_record.slug, target_url=link_record.target_url, status=link_record.status
        )


class MapToListLinksResponse(ts.Mapper, client.ListLinksResponse):

    def __init__(self, list_campaigns_response: ports.ListCampaignsResponse) -> None:
        super().__init__(
            links=tuple(
                MapToLinkViewFromRecord(link_record=link_record)
                for campaign_record in list_campaigns_response.campaigns
                for link_record in campaign_record.links
            )
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
        try:
            campaign = domain.Campaign(MapToCampaignSpec(
                create_campaign_request=create_campaign_request,
                issue_campaign_identity_response=issue_campaign_identity_response,
                short_links_spec=domain.ShortLinksSpec(links=()),
            ))
        except errors.DomainError as domain_error:
            raise client.Rejected(
                code=domain_error.code, message=domain_error.message
            ) from domain_error
        save_campaign_request = MapToSaveCampaignRequest(campaign=campaign)
        find_campaign_view_request = ports.FindCampaignViewRequest(
            campaign_id=save_campaign_request.id,
        )
        try:
            self._campaign_repository.save(save_campaign_request)
            find_campaign_view_response = self._campaign_queries.find_view(
                find_campaign_view_request
            )
        except ports.StoreUnavailable as store_error:
            raise client.Unavailable(
                message="the campaign store is unavailable"
            ) from store_error
        return MapToCampaignView(
            find_campaign_view_request=find_campaign_view_request,
            find_campaign_view_response=find_campaign_view_response,
        )

    def add_link(self, add_link_request: client.AddLinkRequest) -> client.CampaignView:
        try:
            slug = domain.Slug(add_link_request.slug)
            target_url = domain.TargetURL(add_link_request.target_url)
            campaign_id = domain.CampaignID(add_link_request.campaign_id)
        except errors.DomainError as domain_error:
            raise client.Rejected(
                code=domain_error.code, message=domain_error.message
            ) from domain_error
        try:
            check_target_response = self._target_policy.check(
                MapToCheckTargetRequest(target_url=target_url)
            )
        except ports.PolicyUnavailable as policy_error:
            raise client.Unavailable(
                message="the link policy is unavailable"
            ) from policy_error
        try:
            slug_taken_response = self._campaign_repository.slug_taken(
                MapToSlugTakenRequest(slug=slug)
            )
        except ports.StoreUnavailable as store_error:
            raise client.Unavailable(
                message="the campaign store is unavailable"
            ) from store_error
        short_link_spec = MapToShortLinkSpec(
            add_link_request=add_link_request,
            check_target_response=check_target_response,
            slug_taken_response=slug_taken_response,
        )
        find_campaign_request = MapToFindCampaignRequest(campaign_id=campaign_id)
        try:
            find_campaign_response = self._campaign_repository.find(find_campaign_request)
        except ports.StoreUnavailable as store_error:
            raise client.Unavailable(
                message="the campaign store is unavailable"
            ) from store_error
        try:
            campaign = domain.Campaign(MapToCampaignSpecFromRecord(
                find_campaign_request=find_campaign_request,
                find_campaign_response=find_campaign_response,
            ))
        except errors.DomainError as domain_error:
            raise client.Unreadable(
                message=f"stored campaign {find_campaign_request.campaign_id!r} cannot be read back"
            ) from domain_error
        try:
            campaign.add_short_link(short_link_spec)
        except errors.DomainError as domain_error:
            raise client.Conflict(
                code=domain_error.code, message=domain_error.message
            ) from domain_error
        find_campaign_view_request = MapToFindCampaignViewRequest(campaign_id=campaign_id)
        try:
            self._campaign_repository.save(MapToSaveCampaignRequest(campaign=campaign))
            find_campaign_view_response = self._campaign_queries.find_view(
                find_campaign_view_request
            )
        except ports.StoreUnavailable as store_error:
            raise client.Unavailable(
                message="the campaign store is unavailable"
            ) from store_error
        return MapToCampaignView(
            find_campaign_view_request=find_campaign_view_request,
            find_campaign_view_response=find_campaign_view_response,
        )

    def deactivate_link(
        self, deactivate_link_request: client.DeactivateLinkRequest
    ) -> client.CampaignView:
        try:
            campaign_id = domain.CampaignID(deactivate_link_request.campaign_id)
        except errors.DomainError as domain_error:
            raise client.Rejected(
                code=domain_error.code, message=domain_error.message
            ) from domain_error
        find_campaign_request = MapToFindCampaignRequest(campaign_id=campaign_id)
        try:
            find_campaign_response = self._campaign_repository.find(find_campaign_request)
        except ports.StoreUnavailable as store_error:
            raise client.Unavailable(
                message="the campaign store is unavailable"
            ) from store_error
        try:
            campaign = domain.Campaign(MapToCampaignSpecFromRecord(
                find_campaign_request=find_campaign_request,
                find_campaign_response=find_campaign_response,
            ))
        except errors.DomainError as domain_error:
            raise client.Unreadable(
                message=f"stored campaign {find_campaign_request.campaign_id!r} cannot be read back"
            ) from domain_error
        try:
            slug = domain.Slug(deactivate_link_request.slug)
        except errors.DomainError as domain_error:
            raise client.Rejected(
                code=domain_error.code, message=domain_error.message
            ) from domain_error
        try:
            campaign.deactivate_short_link(slug)
        except errors.DomainError as domain_error:
            raise client.Missing(
                code=domain_error.code, message=domain_error.message
            ) from domain_error
        find_campaign_view_request = MapToFindCampaignViewRequest(campaign_id=campaign_id)
        try:
            self._campaign_repository.save(MapToSaveCampaignRequest(campaign=campaign))
            find_campaign_view_response = self._campaign_queries.find_view(
                find_campaign_view_request
            )
        except ports.StoreUnavailable as store_error:
            raise client.Unavailable(
                message="the campaign store is unavailable"
            ) from store_error
        return MapToCampaignView(
            find_campaign_view_request=find_campaign_view_request,
            find_campaign_view_response=find_campaign_view_response,
        )

    def get_campaign(
        self, get_campaign_request: client.GetCampaignRequest
    ) -> client.CampaignView:
        try:
            campaign_id = domain.CampaignID(get_campaign_request.campaign_id)
        except errors.DomainError as domain_error:
            raise client.Rejected(
                code=domain_error.code, message=domain_error.message
            ) from domain_error
        find_campaign_view_request = MapToFindCampaignViewRequest(campaign_id=campaign_id)
        try:
            find_campaign_view_response = self._campaign_queries.find_view(
                find_campaign_view_request
            )
        except ports.StoreUnavailable as store_error:
            raise client.Unavailable(
                message="the campaign store is unavailable"
            ) from store_error
        return MapToCampaignView(
            find_campaign_view_request=find_campaign_view_request,
            find_campaign_view_response=find_campaign_view_response,
        )

    def resolve(self, resolve_request: client.ResolveRequest) -> client.ResolveResponse:
        try:
            slug = domain.Slug(resolve_request.slug)
        except errors.DomainError as domain_error:
            raise client.Rejected(
                code=domain_error.code, message=domain_error.message
            ) from domain_error
        find_campaign_by_slug_request = MapToFindCampaignBySlugRequest(slug=slug)
        try:
            find_campaign_response = self._campaign_repository.find_by_slug(
                find_campaign_by_slug_request
            )
        except ports.StoreUnavailable as store_error:
            raise client.Unavailable(
                message="the campaign store is unavailable"
            ) from store_error
        try:
            campaign = domain.Campaign(MapToCampaignSpecFromSlugLookup(
                find_campaign_by_slug_request=find_campaign_by_slug_request,
                find_campaign_response=find_campaign_response,
            ))
        except errors.DomainError as domain_error:
            raise client.Unreadable(
                message=f"the campaign holding slug {find_campaign_by_slug_request.slug!r} cannot be read back"
            ) from domain_error
        try:
            target_url = campaign.active_target(slug)
        except errors.DomainError as domain_error:
            raise client.Missing(
                code=domain_error.code, message=domain_error.message
            ) from domain_error
        return MapToResolveResponse(target_url=target_url)

    def list_links(
        self, list_links_request: client.ListLinksRequest
    ) -> client.ListLinksResponse:
        try:
            list_campaigns_response = self._campaign_repository.all(
                ports.ListCampaignsRequest()
            )
        except ports.StoreUnavailable as store_error:
            raise client.Unavailable(
                message="the campaign store is unavailable"
            ) from store_error
        return MapToListLinksResponse(list_campaigns_response=list_campaigns_response)
