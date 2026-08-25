from __future__ import annotations

import typing

import tesser.application as ts

import campaign.application.ports.campaign_identity as campaign_identity
import campaign.application.ports.campaign_queries as campaign_queries
import campaign.application.ports.campaign_repository as campaign_repository
import campaign.application.ports.target_policy as target_policy
import campaign.application.views as campaign_views
import campaign.client.client as client
import campaign.domain.campaign as campaign
import campaign.domain.money as money
import campaign.domain.short_link as short_link
import campaign.domain.short_links as short_links
import campaign.domain.values as values
import kernel.slug as kernel_slug
import tesser.errors as errors


class MapToMoneySpec(ts.Mapper, money.MoneySpec):

    def __init__(self, create_campaign_request: client.CreateCampaignRequest) -> None:
        super().__init__(
            amount=create_campaign_request.budget_amount,
            currency=create_campaign_request.budget_currency,
        )


class MapToCampaignSpec(ts.Mapper, campaign.CampaignSpec):

    def __init__(
        self,
        create_campaign_request: client.CreateCampaignRequest,
        issued_campaign_identity: campaign_identity.IssueCampaignIdentityResponse,
        links: short_links.ShortLinksSpec,
    ) -> None:
        super().__init__(
            id=issued_campaign_identity.campaign_id,
            budget=MapToMoneySpec(create_campaign_request=create_campaign_request),
            links=links,
        )


class MapToMoneyRecord(ts.Mapper, campaign_repository.MoneyRecord):

    def __init__(self, campaign_aggregate: campaign.Campaign) -> None:
        super().__init__(
            amount=str(campaign_aggregate.budget.amount),
            currency=str(campaign_aggregate.budget.currency),
        )


class MapToLinkRecord(ts.Mapper, campaign_repository.LinkRecord):

    def __init__(self, short_link_entity: short_link.ShortLink) -> None:
        super().__init__(
            slug=str(short_link_entity.slug),
            target_url=str(short_link_entity.target_url),
            status=str(short_link_entity.status),
        )


class MapToSaveCampaignRequest(ts.Mapper, campaign_repository.SaveCampaignRequest):

    def __init__(self, campaign_aggregate: campaign.Campaign) -> None:
        super().__init__(
            id=str(campaign_aggregate.id),
            budget=MapToMoneyRecord(campaign_aggregate=campaign_aggregate),
            links=tuple(
                MapToLinkRecord(short_link_entity=link) for link in campaign_aggregate.links
            ),
        )


class MapToLinkView(ts.Mapper, client.LinkView):

    def __init__(self, link_row: campaign_queries.LinkViewRow) -> None:
        super().__init__(
            slug=link_row.slug, target_url=link_row.target_url, status=link_row.status
        )


class MapToCampaignView(ts.Mapper, client.CampaignView):

    def __init__(
        self,
        find_campaign_view_request: campaign_queries.FindCampaignViewRequest,
        found_campaign_view: campaign_queries.FindCampaignViewResponse,
    ) -> None:
        match found_campaign_view.outcome:
            case campaign_queries.CampaignViewLookup.FOUND:
                row = found_campaign_view.campaigns[0]
            case campaign_queries.CampaignViewLookup.MISSING:
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
            links=tuple(MapToLinkView(link_row=link) for link in row.links),
        )


class MapToCheckTargetRequest(ts.Mapper, target_policy.CheckTargetRequest):

    def __init__(self, target_url: values.TargetURL) -> None:
        super().__init__(target_url=str(target_url))


class MapToSlugTakenRequest(ts.Mapper, campaign_repository.SlugTakenRequest):

    def __init__(self, slug: kernel_slug.Slug) -> None:
        super().__init__(slug=str(slug))


class MapToShortLinkSpec(ts.Mapper, short_link.ShortLinkSpec):

    def __init__(
        self,
        add_link_request: client.AddLinkRequest,
        checked_target: target_policy.CheckTargetResponse,
        slug_taken: campaign_repository.SlugTakenResponse,
    ) -> None:
        match checked_target.verdict:
            case target_policy.PolicyVerdict.ALLOWED:
                pass
            case target_policy.PolicyVerdict.BLOCKED:
                raise errors.conflict(
                    "destination_blocked", f"destination not allowed: {checked_target.reason}"
                )
            case _ as unreachable:
                typing.assert_never(unreachable)
        match slug_taken.availability:
            case campaign_repository.SlugAvailability.FREE:
                pass
            case campaign_repository.SlugAvailability.TAKEN:
                raise errors.conflict(
                    "duplicate_slug", f"slug {add_link_request.slug!r} already exists"
                )
            case _ as unreachable_availability:
                typing.assert_never(unreachable_availability)
        super().__init__(
            slug=add_link_request.slug, target_url=add_link_request.target_url, active=True
        )


class MapToCampaignSpecFromRecord(ts.Mapper, campaign.CampaignSpec):

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
                    f"no campaign with id {find_campaign_request.campaign_id!r}",
                )
            case _ as unreachable:
                typing.assert_never(unreachable)
        super().__init__(
            id=record.id,
            budget=money.MoneySpec(amount=record.budget.amount, currency=record.budget.currency),
            links=short_links.ShortLinksSpec(links=tuple(
                short_link.ShortLinkSpec(
                    slug=link_record.slug,
                    target_url=link_record.target_url,
                    active=link_record.status == "active",
                )
                for link_record in record.links
            )),
        )


class CampaignService(ts.ApplicationService):

    def __init__(
        self,
        repo: campaign_repository.CampaignRepository,
        policy: target_policy.TargetPolicy,
        identity_gateway: campaign_identity.CampaignIdentity,
        queries: campaign_queries.CampaignQueries,
    ) -> None:
        self._repo = repo
        self._policy = policy
        self._identity_gateway = identity_gateway
        self._queries = queries

    def create_campaign(self, req: client.CreateCampaignRequest) -> client.CampaignView:
        issued_campaign_identity = self._identity_gateway.issue(
            campaign_identity.IssueCampaignIdentityRequest()
        )
        c = campaign.Campaign(MapToCampaignSpec(
            create_campaign_request=req,
            issued_campaign_identity=issued_campaign_identity,
            links=short_links.ShortLinksSpec(links=()),
        ))
        save_request = MapToSaveCampaignRequest(campaign_aggregate=c)
        self._repo.save(save_request)
        find_campaign_view_request = campaign_queries.FindCampaignViewRequest(
            campaign_id=save_request.id,
        )
        found_campaign_view = self._queries.find_view(find_campaign_view_request)
        return MapToCampaignView(
            find_campaign_view_request=find_campaign_view_request,
            found_campaign_view=found_campaign_view,
        )

    def add_link(self, req: client.AddLinkRequest) -> client.CampaignView:
        slug = kernel_slug.Slug(req.slug)
        target_url = values.TargetURL(req.target_url)
        campaign_id = values.CampaignID(req.campaign_id)
        campaign_id_text = str(campaign_id)
        checked_target = self._policy.check(MapToCheckTargetRequest(target_url=target_url))
        slug_taken = self._repo.slug_taken(MapToSlugTakenRequest(slug=slug))
        short_link_spec = MapToShortLinkSpec(
            add_link_request=req,
            checked_target=checked_target,
            slug_taken=slug_taken,
        )
        find_campaign_request = campaign_repository.FindCampaignRequest(
            campaign_id=campaign_id_text
        )
        found_campaign = self._repo.find(find_campaign_request)
        c = campaign.Campaign(MapToCampaignSpecFromRecord(
            find_campaign_request=find_campaign_request,
            found_campaign=found_campaign,
        ))
        c.add_short_link(short_link_spec)
        self._repo.save(MapToSaveCampaignRequest(campaign_aggregate=c))
        find_campaign_view_request = campaign_queries.FindCampaignViewRequest(
            campaign_id=campaign_id_text,
        )
        found_campaign_view = self._queries.find_view(find_campaign_view_request)
        return MapToCampaignView(
            find_campaign_view_request=find_campaign_view_request,
            found_campaign_view=found_campaign_view,
        )

    def deactivate_link(self, req: client.DeactivateLinkRequest) -> client.CampaignView:
        campaign_id = values.CampaignID(req.campaign_id)
        campaign_id_text = str(campaign_id)
        find_campaign_request = campaign_repository.FindCampaignRequest(
            campaign_id=campaign_id_text
        )
        found_campaign = self._repo.find(find_campaign_request)
        c = campaign.Campaign(MapToCampaignSpecFromRecord(
            find_campaign_request=find_campaign_request,
            found_campaign=found_campaign,
        ))
        c.deactivate_short_link(kernel_slug.Slug(req.slug))
        self._repo.save(MapToSaveCampaignRequest(campaign_aggregate=c))
        find_campaign_view_request = campaign_queries.FindCampaignViewRequest(
            campaign_id=campaign_id_text,
        )
        found_campaign_view = self._queries.find_view(find_campaign_view_request)
        return MapToCampaignView(
            find_campaign_view_request=find_campaign_view_request,
            found_campaign_view=found_campaign_view,
        )

    def get_campaign(self, req: client.GetCampaignRequest) -> client.CampaignView:
        campaign_id = values.CampaignID(req.campaign_id)
        campaign_id_text = str(campaign_id)
        find_campaign_view_request = campaign_queries.FindCampaignViewRequest(
            campaign_id=campaign_id_text,
        )
        found_campaign_view = self._queries.find_view(find_campaign_view_request)
        return MapToCampaignView(
            find_campaign_view_request=find_campaign_view_request,
            found_campaign_view=found_campaign_view,
        )

    def resolve(self, req: client.ResolveRequest) -> client.ResolveResponse:
        slug = kernel_slug.Slug(req.slug)
        slug_text = str(slug)
        find_campaign_by_slug_request = campaign_repository.FindCampaignBySlugRequest(
            slug=slug_text
        )
        found = self._repo.find_by_slug(find_campaign_by_slug_request)
        c = campaign.Campaign(campaign_views.MapToCampaignSpecFromSlugLookup(
            find_campaign_by_slug_request=find_campaign_by_slug_request,
            found_campaign=found,
        ))
        target_url = c.active_target(slug)
        target_url_text = str(target_url)
        return client.ResolveResponse(target_url=target_url_text)

    def list_links(self, req: client.ListLinksRequest) -> client.ListLinksResponse:
        listed = self._repo.all(campaign_repository.ListCampaignsRequest())
        views: list[client.LinkView] = []
        for listed_campaign in listed.campaigns:
            for link in listed_campaign.links:
                view = client.LinkView(
                    slug=link.slug, target_url=link.target_url, status=link.status
                )
                views.append(view)
        listed_views = tuple(views)
        return client.ListLinksResponse(links=listed_views)
