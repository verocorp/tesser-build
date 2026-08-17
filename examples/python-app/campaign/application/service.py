from __future__ import annotations

import tesser.application as ts

import campaign.application.ports.campaign_identity as campaign_identity
import campaign.application.ports.campaign_repository as campaign_repository
import campaign.application.ports.target_policy as target_policy
import campaign.application.views as campaign_views
import campaign.client.client as client
import campaign.domain.campaign as campaign
import campaign.domain.money as money
import campaign.domain.short_link as short_link
import campaign.domain.values as values


class MapToMoneySpec(ts.Mapper):

    def __init__(self, create_campaign_request: client.CreateCampaignRequest) -> None:
        self._create_campaign_request = create_campaign_request
        self._amount = create_campaign_request.budget_amount
        self._currency = create_campaign_request.budget_currency

    @property
    def create_campaign_request(self) -> client.CreateCampaignRequest:
        return self._create_campaign_request

    @property
    def amount(self) -> str:
        return self._amount

    @property
    def currency(self) -> str:
        return self._currency


class MapToCampaignSpec(ts.Mapper):

    def __init__(
        self,
        create_campaign_request: client.CreateCampaignRequest,
        issued_campaign_identity: campaign_identity.IssueCampaignIdentityResponse,
        links: tuple[short_link.ShortLinkSpec, ...],
    ) -> None:
        self._create_campaign_request = create_campaign_request
        self._issued_campaign_identity = issued_campaign_identity
        self._campaign_id = issued_campaign_identity.campaign_id
        self._budget_mapper = MapToMoneySpec(create_campaign_request=create_campaign_request)
        self._links = links

    @property
    def create_campaign_request(self) -> client.CreateCampaignRequest:
        return self._create_campaign_request

    @property
    def issued_campaign_identity(self) -> campaign_identity.IssueCampaignIdentityResponse:
        return self._issued_campaign_identity

    @property
    def campaign_id(self) -> str:
        return self._campaign_id

    @property
    def budget_mapper(self) -> MapToMoneySpec:
        return self._budget_mapper

    @property
    def links(self) -> tuple[short_link.ShortLinkSpec, ...]:
        return self._links


class MapToMoneyRecord(ts.Mapper):

    def __init__(self, campaign_aggregate: campaign.Campaign) -> None:
        self._campaign_aggregate = campaign_aggregate
        self._amount = str(campaign_aggregate.budget.amount)
        self._currency = str(campaign_aggregate.budget.currency)

    @property
    def campaign_aggregate(self) -> campaign.Campaign:
        return self._campaign_aggregate

    @property
    def amount(self) -> str:
        return self._amount

    @property
    def currency(self) -> str:
        return self._currency


class MapToSaveCampaignRequest(ts.Mapper):

    def __init__(self, campaign_aggregate: campaign.Campaign) -> None:
        record_links: list[campaign_repository.LinkRecord] = []
        for link in campaign_aggregate.links:
            record_slug = str(link.slug)
            record_target_url = str(link.target_url)
            record_status = str(link.status)
            record_links.append(campaign_repository.LinkRecord(
                slug=record_slug,
                target_url=record_target_url,
                status=record_status,
            ))
        self._campaign_aggregate = campaign_aggregate
        self._record_id = str(campaign_aggregate.id)
        self._money_record_mapper = MapToMoneyRecord(campaign_aggregate=campaign_aggregate)
        self._link_records = tuple(record_links)

    @property
    def campaign_aggregate(self) -> campaign.Campaign:
        return self._campaign_aggregate

    @property
    def record_id(self) -> str:
        return self._record_id

    @property
    def money_record_mapper(self) -> MapToMoneyRecord:
        return self._money_record_mapper

    @property
    def link_records(self) -> tuple[campaign_repository.LinkRecord, ...]:
        return self._link_records


class MapToCampaignView(ts.Mapper):

    def __init__(self, campaign_aggregate: campaign.Campaign) -> None:
        link_views: list[client.LinkView] = []
        for link in campaign_aggregate.links:
            view_slug = str(link.slug)
            view_target_url = str(link.target_url)
            view_status = str(link.status)
            link_views.append(client.LinkView(
                slug=view_slug,
                target_url=view_target_url,
                status=view_status,
            ))
        self._campaign_aggregate = campaign_aggregate
        self._campaign_id = str(campaign_aggregate.id)
        self._budget_amount = str(campaign_aggregate.budget.amount)
        self._budget_currency = str(campaign_aggregate.budget.currency)
        self._link_views = tuple(link_views)

    @property
    def campaign_aggregate(self) -> campaign.Campaign:
        return self._campaign_aggregate

    @property
    def campaign_id(self) -> str:
        return self._campaign_id

    @property
    def budget_amount(self) -> str:
        return self._budget_amount

    @property
    def budget_currency(self) -> str:
        return self._budget_currency

    @property
    def link_views(self) -> tuple[client.LinkView, ...]:
        return self._link_views


class CampaignService(ts.ApplicationService):

    def __init__(
        self,
        repo: campaign_repository.CampaignRepository,
        policy: target_policy.TargetPolicy,
        identity_gateway: campaign_identity.CampaignIdentity,
    ) -> None:
        self._repo = repo
        self._policy = policy
        self._identity_gateway = identity_gateway

    def create_campaign(self, req: client.CreateCampaignRequest) -> client.CampaignView:  # tessercheck:ignore TB082
        issued_campaign_identity = self._identity_gateway.issue(
            campaign_identity.IssueCampaignIdentityRequest()
        )
        campaign_spec_mapper = MapToCampaignSpec(
            create_campaign_request=req,
            issued_campaign_identity=issued_campaign_identity,
            links=(),
        )
        c = campaign.Campaign(campaign.CampaignSpec(
            id=campaign_spec_mapper.campaign_id,
            budget=money.MoneySpec(
                amount=campaign_spec_mapper.budget_mapper.amount,
                currency=campaign_spec_mapper.budget_mapper.currency,
            ),
            links=campaign_spec_mapper.links,
        ))

        save_request_mapper = MapToSaveCampaignRequest(campaign_aggregate=c)
        self._repo.save(campaign_repository.SaveCampaignRequest(
            id=save_request_mapper.record_id,
            budget=campaign_repository.MoneyRecord(
                amount=save_request_mapper.money_record_mapper.amount,
                currency=save_request_mapper.money_record_mapper.currency,
            ),
            links=save_request_mapper.link_records,
        ))

        campaign_view_mapper = MapToCampaignView(campaign_aggregate=c)
        return client.CampaignView(
            campaign_id=campaign_view_mapper.campaign_id,
            budget_amount=campaign_view_mapper.budget_amount,
            budget_currency=campaign_view_mapper.budget_currency,
            links=campaign_view_mapper.link_views,
        )

    def add_link(self, req: client.AddLinkRequest) -> client.CampaignView:
        slug = str(values.Slug(req.slug))
        target_url = str(values.TargetURL(req.target_url))
        campaign_views.ensure_target_allowed(self._policy.check(target_policy.CheckTargetRequest(target_url=target_url)))
        campaign_views.ensure_slug_available(self._repo.slug_taken(campaign_repository.SlugTakenRequest(slug=slug)), slug)
        found = self._repo.find(campaign_repository.FindCampaignRequest(campaign_id=req.campaign_id))
        c = campaign_views.required_campaign(found, req.campaign_id)
        c.add_short_link(short_link.ShortLinkSpec(slug=req.slug, target_url=req.target_url, active=True))
        self._repo.save(campaign_views.save_request(c))
        return campaign_views.campaign_view(c)

    def deactivate_link(self, req: client.DeactivateLinkRequest) -> client.CampaignView:
        found = self._repo.find(campaign_repository.FindCampaignRequest(campaign_id=req.campaign_id))
        c = campaign_views.required_campaign(found, req.campaign_id)
        c.deactivate_short_link(values.Slug(req.slug))
        self._repo.save(campaign_views.save_request(c))
        return campaign_views.campaign_view(c)

    def get_campaign(self, req: client.GetCampaignRequest) -> client.CampaignView:
        found = self._repo.find(campaign_repository.FindCampaignRequest(campaign_id=req.campaign_id))
        c = campaign_views.required_campaign(found, req.campaign_id)
        return campaign_views.campaign_view(c)

    def resolve(self, req: client.ResolveRequest) -> client.ResolveResponse:
        slug = str(values.Slug(req.slug))
        found = self._repo.find_by_slug(campaign_repository.FindCampaignBySlugRequest(slug=slug))
        return client.ResolveResponse(target_url=campaign_views.resolved_target(found, slug))

    def list_links(self, req: client.ListLinksRequest) -> client.ListLinksResponse:
        listed = self._repo.all(campaign_repository.ListCampaignsRequest())
        views = tuple(
            campaign_views.link_view(link) for c in listed.campaigns for link in c.links
        )
        return client.ListLinksResponse(links=views)
