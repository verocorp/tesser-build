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
        links: short_links.ShortLinksSpec,
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
    def links(self) -> short_links.ShortLinksSpec:
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


class MapToLinkRecord(ts.Mapper):

    def __init__(self, short_link_entity: short_link.ShortLink) -> None:
        self._short_link_entity = short_link_entity
        self._slug = str(short_link_entity.slug)
        self._target_url = str(short_link_entity.target_url)
        self._status = str(short_link_entity.status)

    @property
    def short_link_entity(self) -> short_link.ShortLink:
        return self._short_link_entity

    @property
    def slug(self) -> str:
        return self._slug

    @property
    def target_url(self) -> str:
        return self._target_url

    @property
    def status(self) -> str:
        return self._status


class MapToSaveCampaignRequest(ts.Mapper):

    def __init__(self, campaign_aggregate: campaign.Campaign) -> None:
        link_record_mappers: list[MapToLinkRecord] = []
        for link in campaign_aggregate.links:
            link_record_mappers.append(MapToLinkRecord(short_link_entity=link))
        self._campaign_aggregate = campaign_aggregate
        self._record_id = str(campaign_aggregate.id)
        self._money_record_mapper = MapToMoneyRecord(campaign_aggregate=campaign_aggregate)
        self._link_record_mappers = tuple(link_record_mappers)

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
    def link_record_mappers(self) -> tuple[MapToLinkRecord, ...]:
        return self._link_record_mappers


class MapToCampaignView(ts.Mapper):

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
        self._find_campaign_view_request = find_campaign_view_request
        self._found_campaign_view = found_campaign_view
        self._campaign_id = row.campaign_id
        self._budget_amount = row.budget_amount
        self._budget_currency = row.budget_currency
        self._link_rows = tuple(row.links)

    @property
    def find_campaign_view_request(self) -> campaign_queries.FindCampaignViewRequest:
        return self._find_campaign_view_request

    @property
    def found_campaign_view(self) -> campaign_queries.FindCampaignViewResponse:
        return self._found_campaign_view

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
    def link_rows(self) -> tuple[campaign_queries.LinkViewRow, ...]:
        return self._link_rows


class MapToCheckTargetRequest(ts.Mapper):

    def __init__(self, target_url: values.TargetURL) -> None:
        self._target_url_value = target_url
        self._target_url = str(target_url)

    @property
    def target_url_value(self) -> values.TargetURL:
        return self._target_url_value

    @property
    def target_url(self) -> str:
        return self._target_url


class MapToSlugTakenRequest(ts.Mapper):

    def __init__(self, slug: kernel_slug.Slug) -> None:
        self._slug_value = slug
        self._slug = str(slug)

    @property
    def slug_value(self) -> kernel_slug.Slug:
        return self._slug_value

    @property
    def slug(self) -> str:
        return self._slug


class MapToShortLinkSpec(ts.Mapper):

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
        self._add_link_request = add_link_request
        self._checked_target = checked_target
        self._slug_taken = slug_taken
        self._slug = add_link_request.slug
        self._target_url = add_link_request.target_url

    @property
    def add_link_request(self) -> client.AddLinkRequest:
        return self._add_link_request

    @property
    def checked_target(self) -> target_policy.CheckTargetResponse:
        return self._checked_target

    @property
    def slug_taken(self) -> campaign_repository.SlugTakenResponse:
        return self._slug_taken

    @property
    def slug(self) -> str:
        return self._slug

    @property
    def target_url(self) -> str:
        return self._target_url


class MapToCampaignSpecFromRecord(ts.Mapper):

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
        self._find_campaign_request = find_campaign_request
        self._found_campaign = found_campaign
        self._campaign_id = record.id
        self._budget_amount = record.budget.amount
        self._budget_currency = record.budget.currency
        self._link_records = tuple(record.links)

    @property
    def find_campaign_request(self) -> campaign_repository.FindCampaignRequest:
        return self._find_campaign_request

    @property
    def found_campaign(self) -> campaign_repository.FindCampaignResponse:
        return self._found_campaign

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
    def link_records(self) -> tuple[campaign_repository.LinkRecord, ...]:
        return self._link_records


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
        campaign_spec_mapper = MapToCampaignSpec(
            create_campaign_request=req,
            issued_campaign_identity=issued_campaign_identity,
            links=short_links.ShortLinksSpec(links=()),
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
        link_records = tuple(
            campaign_repository.LinkRecord(
                slug=link_record_mapper.slug,
                target_url=link_record_mapper.target_url,
                status=link_record_mapper.status,
            )
            for link_record_mapper in save_request_mapper.link_record_mappers
        )
        self._repo.save(campaign_repository.SaveCampaignRequest(
            id=save_request_mapper.record_id,
            budget=campaign_repository.MoneyRecord(
                amount=save_request_mapper.money_record_mapper.amount,
                currency=save_request_mapper.money_record_mapper.currency,
            ),
            links=link_records,
        ))

        find_campaign_view_request = campaign_queries.FindCampaignViewRequest(
            campaign_id=save_request_mapper.record_id,
        )
        found_campaign_view = self._queries.find_view(find_campaign_view_request)
        campaign_view_mapper = MapToCampaignView(
            find_campaign_view_request=find_campaign_view_request,
            found_campaign_view=found_campaign_view,
        )
        link_views = tuple(
            client.LinkView(slug=link.slug, target_url=link.target_url, status=link.status)
            for link in campaign_view_mapper.link_rows
        )
        return client.CampaignView(
            campaign_id=campaign_view_mapper.campaign_id,
            budget_amount=campaign_view_mapper.budget_amount,
            budget_currency=campaign_view_mapper.budget_currency,
            links=link_views,
        )

    def add_link(self, req: client.AddLinkRequest) -> client.CampaignView:
        slug = kernel_slug.Slug(req.slug)
        target_url = values.TargetURL(req.target_url)
        campaign_id = values.CampaignID(req.campaign_id)
        campaign_id_text = str(campaign_id)
        check_target_request_mapper = MapToCheckTargetRequest(target_url=target_url)
        checked_target = self._policy.check(target_policy.CheckTargetRequest(
            target_url=check_target_request_mapper.target_url,
        ))
        slug_taken_request_mapper = MapToSlugTakenRequest(slug=slug)
        slug_taken = self._repo.slug_taken(campaign_repository.SlugTakenRequest(
            slug=slug_taken_request_mapper.slug,
        ))
        short_link_spec_mapper = MapToShortLinkSpec(
            add_link_request=req,
            checked_target=checked_target,
            slug_taken=slug_taken,
        )
        find_campaign_request = campaign_repository.FindCampaignRequest(
            campaign_id=campaign_id_text
        )
        found_campaign = self._repo.find(find_campaign_request)
        campaign_spec_mapper = MapToCampaignSpecFromRecord(
            find_campaign_request=find_campaign_request,
            found_campaign=found_campaign,
        )
        link_specs = tuple(
            short_link.ShortLinkSpec(
                slug=link_record.slug,
                target_url=link_record.target_url,
                active=link_record.status == "active",
            )
            for link_record in campaign_spec_mapper.link_records
        )
        links_spec = short_links.ShortLinksSpec(links=link_specs)
        c = campaign.Campaign(campaign.CampaignSpec(
            id=campaign_spec_mapper.campaign_id,
            budget=money.MoneySpec(
                amount=campaign_spec_mapper.budget_amount,
                currency=campaign_spec_mapper.budget_currency,
            ),
            links=links_spec,
        ))
        c.add_short_link(short_link.ShortLinkSpec(
            slug=short_link_spec_mapper.slug,
            target_url=short_link_spec_mapper.target_url,
            active=True,
        ))

        save_request_mapper = MapToSaveCampaignRequest(campaign_aggregate=c)
        link_records = tuple(
            campaign_repository.LinkRecord(
                slug=link_record_mapper.slug,
                target_url=link_record_mapper.target_url,
                status=link_record_mapper.status,
            )
            for link_record_mapper in save_request_mapper.link_record_mappers
        )
        self._repo.save(campaign_repository.SaveCampaignRequest(
            id=save_request_mapper.record_id,
            budget=campaign_repository.MoneyRecord(
                amount=save_request_mapper.money_record_mapper.amount,
                currency=save_request_mapper.money_record_mapper.currency,
            ),
            links=link_records,
        ))

        find_campaign_view_request = campaign_queries.FindCampaignViewRequest(
            campaign_id=campaign_id_text,
        )
        found_campaign_view = self._queries.find_view(find_campaign_view_request)
        campaign_view_mapper = MapToCampaignView(
            find_campaign_view_request=find_campaign_view_request,
            found_campaign_view=found_campaign_view,
        )
        link_views = tuple(
            client.LinkView(slug=link.slug, target_url=link.target_url, status=link.status)
            for link in campaign_view_mapper.link_rows
        )
        return client.CampaignView(
            campaign_id=campaign_view_mapper.campaign_id,
            budget_amount=campaign_view_mapper.budget_amount,
            budget_currency=campaign_view_mapper.budget_currency,
            links=link_views,
        )

    def deactivate_link(self, req: client.DeactivateLinkRequest) -> client.CampaignView:
        campaign_id = values.CampaignID(req.campaign_id)
        campaign_id_text = str(campaign_id)
        find_campaign_request = campaign_repository.FindCampaignRequest(
            campaign_id=campaign_id_text
        )
        found_campaign = self._repo.find(find_campaign_request)
        campaign_spec_mapper = MapToCampaignSpecFromRecord(
            find_campaign_request=find_campaign_request,
            found_campaign=found_campaign,
        )
        link_specs = tuple(
            short_link.ShortLinkSpec(
                slug=link_record.slug,
                target_url=link_record.target_url,
                active=link_record.status == "active",
            )
            for link_record in campaign_spec_mapper.link_records
        )
        links_spec = short_links.ShortLinksSpec(links=link_specs)
        c = campaign.Campaign(campaign.CampaignSpec(
            id=campaign_spec_mapper.campaign_id,
            budget=money.MoneySpec(
                amount=campaign_spec_mapper.budget_amount,
                currency=campaign_spec_mapper.budget_currency,
            ),
            links=links_spec,
        ))
        c.deactivate_short_link(kernel_slug.Slug(req.slug))

        save_request_mapper = MapToSaveCampaignRequest(campaign_aggregate=c)
        link_records = tuple(
            campaign_repository.LinkRecord(
                slug=link_record_mapper.slug,
                target_url=link_record_mapper.target_url,
                status=link_record_mapper.status,
            )
            for link_record_mapper in save_request_mapper.link_record_mappers
        )
        self._repo.save(campaign_repository.SaveCampaignRequest(
            id=save_request_mapper.record_id,
            budget=campaign_repository.MoneyRecord(
                amount=save_request_mapper.money_record_mapper.amount,
                currency=save_request_mapper.money_record_mapper.currency,
            ),
            links=link_records,
        ))

        find_campaign_view_request = campaign_queries.FindCampaignViewRequest(
            campaign_id=campaign_id_text,
        )
        found_campaign_view = self._queries.find_view(find_campaign_view_request)
        campaign_view_mapper = MapToCampaignView(
            find_campaign_view_request=find_campaign_view_request,
            found_campaign_view=found_campaign_view,
        )
        link_views = tuple(
            client.LinkView(slug=link.slug, target_url=link.target_url, status=link.status)
            for link in campaign_view_mapper.link_rows
        )
        return client.CampaignView(
            campaign_id=campaign_view_mapper.campaign_id,
            budget_amount=campaign_view_mapper.budget_amount,
            budget_currency=campaign_view_mapper.budget_currency,
            links=link_views,
        )

    def get_campaign(self, req: client.GetCampaignRequest) -> client.CampaignView:
        campaign_id = values.CampaignID(req.campaign_id)
        campaign_id_text = str(campaign_id)
        find_campaign_view_request = campaign_queries.FindCampaignViewRequest(
            campaign_id=campaign_id_text,
        )
        found_campaign_view = self._queries.find_view(find_campaign_view_request)
        campaign_view_mapper = MapToCampaignView(
            find_campaign_view_request=find_campaign_view_request,
            found_campaign_view=found_campaign_view,
        )
        link_views = tuple(
            client.LinkView(slug=link.slug, target_url=link.target_url, status=link.status)
            for link in campaign_view_mapper.link_rows
        )
        return client.CampaignView(
            campaign_id=campaign_view_mapper.campaign_id,
            budget_amount=campaign_view_mapper.budget_amount,
            budget_currency=campaign_view_mapper.budget_currency,
            links=link_views,
        )

    def resolve(self, req: client.ResolveRequest) -> client.ResolveResponse:
        slug = kernel_slug.Slug(req.slug)
        slug_text = str(slug)
        find_campaign_by_slug_request = campaign_repository.FindCampaignBySlugRequest(
            slug=slug_text
        )
        found = self._repo.find_by_slug(find_campaign_by_slug_request)
        campaign_spec_mapper = campaign_views.MapToCampaignSpecFromSlugLookup(
            find_campaign_by_slug_request=find_campaign_by_slug_request,
            found_campaign=found,
        )
        link_specs = tuple(
            short_link.ShortLinkSpec(
                slug=link_record.slug,
                target_url=link_record.target_url,
                active=link_record.status == "active",
            )
            for link_record in campaign_spec_mapper.link_records
        )
        links_spec = short_links.ShortLinksSpec(links=link_specs)
        c = campaign.Campaign(campaign.CampaignSpec(
            id=campaign_spec_mapper.campaign_id,
            budget=money.MoneySpec(
                amount=campaign_spec_mapper.budget_amount,
                currency=campaign_spec_mapper.budget_currency,
            ),
            links=links_spec,
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
