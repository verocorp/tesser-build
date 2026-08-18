from __future__ import annotations

import pytest
import tesser.testing as ts

import campaign.application.ports.campaign_identity as campaign_identity
import campaign.application.ports.campaign_queries as campaign_queries
import campaign.application.ports.campaign_repository as campaign_repository
import campaign.application.ports.target_policy as target_policy
import campaign.application.service as service
import campaign.client.client as client
import campaign.domain.campaign as campaign
import campaign.domain.money as money
import campaign.domain.short_link as short_link
import campaign.domain.short_links as short_links
from tesser.errors import DomainError, InfraError, Kind


@ts.fake
class FakeCampaignStore(campaign_repository.CampaignRepository):

    def __init__(self) -> None:
        self.rows: dict[str, campaign_repository.CampaignRecord] = {}
        self.saved: list[campaign_repository.SaveCampaignRequest] = []

    def save(
        self, request: campaign_repository.SaveCampaignRequest
    ) -> campaign_repository.SaveCampaignResponse:
        self.saved.append(request)
        self.rows[request.id] = campaign_repository.CampaignRecord(
            id=request.id, budget=request.budget, links=request.links
        )
        return campaign_repository.SaveCampaignResponse()

    def find(
        self, request: campaign_repository.FindCampaignRequest
    ) -> campaign_repository.FindCampaignResponse:
        row = self.rows.get(request.campaign_id)
        if row is None:
            return campaign_repository.FindCampaignResponse(
                outcome=campaign_repository.CampaignLookup.MISSING, campaigns=()
            )
        return campaign_repository.FindCampaignResponse(
            outcome=campaign_repository.CampaignLookup.FOUND, campaigns=(row,)
        )

    def find_by_slug(
        self, request: campaign_repository.FindCampaignBySlugRequest
    ) -> campaign_repository.FindCampaignResponse:
        for row in self.rows.values():
            if any(link.slug == request.slug for link in row.links):
                return campaign_repository.FindCampaignResponse(
                    outcome=campaign_repository.CampaignLookup.FOUND, campaigns=(row,)
                )
        return campaign_repository.FindCampaignResponse(
            outcome=campaign_repository.CampaignLookup.MISSING, campaigns=()
        )

    def slug_taken(
        self, request: campaign_repository.SlugTakenRequest
    ) -> campaign_repository.SlugTakenResponse:
        taken = any(
            link.slug == request.slug for row in self.rows.values() for link in row.links
        )
        return campaign_repository.SlugTakenResponse(
            availability=campaign_repository.SlugAvailability.TAKEN
            if taken
            else campaign_repository.SlugAvailability.FREE
        )

    def all(
        self, request: campaign_repository.ListCampaignsRequest
    ) -> campaign_repository.ListCampaignsResponse:
        return campaign_repository.ListCampaignsResponse(campaigns=tuple(self.rows.values()))

    def find_view(
        self, request: campaign_queries.FindCampaignViewRequest
    ) -> campaign_queries.FindCampaignViewResponse:
        row = self.rows.get(request.campaign_id)
        if row is None:
            return campaign_queries.FindCampaignViewResponse(
                outcome=campaign_queries.CampaignViewLookup.MISSING, campaigns=()
            )
        links: list[campaign_queries.LinkViewRow] = []
        for link in row.links:
            links.append(campaign_queries.LinkViewRow(
                slug=link.slug, target_url=link.target_url, status=link.status
            ))
        view = campaign_queries.CampaignViewRow(
            campaign_id=row.id,
            budget_amount=row.budget.amount,
            budget_currency=row.budget.currency,
            links=tuple(links),
        )
        return campaign_queries.FindCampaignViewResponse(
            outcome=campaign_queries.CampaignViewLookup.FOUND, campaigns=(view,)
        )


@ts.fake
class FakeCampaignIdentity(campaign_identity.CampaignIdentity):

    def __init__(self) -> None:
        self.issued = 0

    def issue(
        self, request: campaign_identity.IssueCampaignIdentityRequest
    ) -> campaign_identity.IssueCampaignIdentityResponse:
        self.issued += 1
        campaign_id = f"{self.issued:016x}"
        return campaign_identity.IssueCampaignIdentityResponse(campaign_id=campaign_id)


@ts.fake
class FakeTargetPolicyAllowing(target_policy.TargetPolicy):

    def __init__(self) -> None:
        self.checked: list[str] = []

    def check(
        self, request: target_policy.CheckTargetRequest
    ) -> target_policy.CheckTargetResponse:
        self.checked.append(request.target_url)
        return target_policy.CheckTargetResponse(
            verdict=target_policy.PolicyVerdict.ALLOWED, reason="clean"
        )


@ts.fake
class FakeTargetPolicyBlocking(target_policy.TargetPolicy):

    def check(
        self, request: target_policy.CheckTargetRequest
    ) -> target_policy.CheckTargetResponse:
        return target_policy.CheckTargetResponse(
            verdict=target_policy.PolicyVerdict.BLOCKED, reason="on the deny-list"
        )


@ts.fake
class FakeTargetPolicyDown(target_policy.TargetPolicy):

    def check(
        self, request: target_policy.CheckTargetRequest
    ) -> target_policy.CheckTargetResponse:
        raise InfraError("linkpolicy unavailable")


def test_create_campaign_returns_the_budget_it_was_asked_for() -> None:
    store = FakeCampaignStore()
    svc = service.CampaignService(store, FakeTargetPolicyAllowing(), FakeCampaignIdentity(), store)

    view = svc.create_campaign(
        client.CreateCampaignRequest(budget_amount="250.00", budget_currency="EUR")
    )

    assert view.budget_amount == "250.00"
    assert view.budget_currency == "EUR"
    assert view.links == ()


def test_create_campaign_persists_the_campaign_it_returns() -> None:
    repo = FakeCampaignStore()
    svc = service.CampaignService(repo, FakeTargetPolicyAllowing(), FakeCampaignIdentity(), repo)

    view = svc.create_campaign(
        client.CreateCampaignRequest(budget_amount="100.00", budget_currency="USD")
    )

    assert [saved.id for saved in repo.saved] == [view.campaign_id]


def test_create_campaign_mints_a_distinct_id_per_campaign() -> None:
    store = FakeCampaignStore()
    svc = service.CampaignService(store, FakeTargetPolicyAllowing(), FakeCampaignIdentity(), store)

    first = svc.create_campaign(
        client.CreateCampaignRequest(budget_amount="100.00", budget_currency="USD")
    )
    second = svc.create_campaign(
        client.CreateCampaignRequest(budget_amount="100.00", budget_currency="USD")
    )

    assert first.campaign_id != second.campaign_id


def test_create_campaign_refuses_a_malformed_currency_and_saves_nothing() -> None:
    repo = FakeCampaignStore()
    svc = service.CampaignService(repo, FakeTargetPolicyAllowing(), FakeCampaignIdentity(), repo)

    with pytest.raises(DomainError) as caught:
        svc.create_campaign(
            client.CreateCampaignRequest(budget_amount="100.00", budget_currency="dollars")
        )

    assert caught.value.code == "invalid_budget_currency"
    assert repo.saved == []


def test_add_link_puts_the_link_on_the_campaign() -> None:
    repo = FakeCampaignStore()
    svc = service.CampaignService(repo, FakeTargetPolicyAllowing(), FakeCampaignIdentity(), repo)
    created = svc.create_campaign(
        client.CreateCampaignRequest(budget_amount="100.00", budget_currency="USD")
    )

    view = svc.add_link(
        client.AddLinkRequest(
            campaign_id=created.campaign_id, slug="promo", target_url="https://ok.example/x"
        )
    )

    assert [(link.slug, link.target_url, link.status) for link in view.links] == [
        ("promo", "https://ok.example/x", "active")
    ]


def test_add_link_asks_the_policy_about_the_target_before_admitting_it() -> None:
    policy = FakeTargetPolicyAllowing()
    store = FakeCampaignStore()
    svc = service.CampaignService(store, policy, FakeCampaignIdentity(), store)
    created = svc.create_campaign(
        client.CreateCampaignRequest(budget_amount="100.00", budget_currency="USD")
    )

    svc.add_link(
        client.AddLinkRequest(
            campaign_id=created.campaign_id, slug="promo", target_url="https://ok.example/x"
        )
    )

    assert policy.checked == ["https://ok.example/x"]


def test_add_link_refuses_a_blocked_destination_and_saves_nothing() -> None:
    repo = FakeCampaignStore()
    allowing = service.CampaignService(repo, FakeTargetPolicyAllowing(), FakeCampaignIdentity(), repo)
    created = allowing.create_campaign(
        client.CreateCampaignRequest(budget_amount="100.00", budget_currency="USD")
    )
    svc = service.CampaignService(repo, FakeTargetPolicyBlocking(), FakeCampaignIdentity(), repo)
    before = len(repo.saved)

    with pytest.raises(DomainError) as caught:
        svc.add_link(
            client.AddLinkRequest(
                campaign_id=created.campaign_id, slug="promo", target_url="https://bad.example/x"
            )
        )

    assert caught.value.kind is Kind.CONFLICT
    assert caught.value.code == "destination_blocked"
    assert "on the deny-list" in caught.value.message
    assert len(repo.saved) == before


def test_add_link_lets_a_policy_outage_surface_and_saves_nothing() -> None:
    repo = FakeCampaignStore()
    allowing = service.CampaignService(repo, FakeTargetPolicyAllowing(), FakeCampaignIdentity(), repo)
    created = allowing.create_campaign(
        client.CreateCampaignRequest(budget_amount="100.00", budget_currency="USD")
    )
    svc = service.CampaignService(repo, FakeTargetPolicyDown(), FakeCampaignIdentity(), repo)
    before = len(repo.saved)

    with pytest.raises(InfraError):
        svc.add_link(
            client.AddLinkRequest(
                campaign_id=created.campaign_id, slug="promo", target_url="https://ok.example/x"
            )
        )

    assert len(repo.saved) == before


def test_add_link_refuses_a_slug_another_campaign_already_uses() -> None:
    repo = FakeCampaignStore()
    svc = service.CampaignService(repo, FakeTargetPolicyAllowing(), FakeCampaignIdentity(), repo)
    first = svc.create_campaign(
        client.CreateCampaignRequest(budget_amount="100.00", budget_currency="USD")
    )
    second = svc.create_campaign(
        client.CreateCampaignRequest(budget_amount="100.00", budget_currency="USD")
    )
    svc.add_link(
        client.AddLinkRequest(
            campaign_id=first.campaign_id, slug="promo", target_url="https://ok.example/x"
        )
    )

    with pytest.raises(DomainError) as caught:
        svc.add_link(
            client.AddLinkRequest(
                campaign_id=second.campaign_id, slug="promo", target_url="https://ok.example/y"
            )
        )

    assert caught.value.kind is Kind.CONFLICT
    assert caught.value.code == "duplicate_slug"


def test_add_link_refuses_a_malformed_slug_without_touching_the_policy() -> None:
    policy = FakeTargetPolicyAllowing()
    store = FakeCampaignStore()
    svc = service.CampaignService(store, policy, FakeCampaignIdentity(), store)

    with pytest.raises(DomainError) as caught:
        svc.add_link(
            client.AddLinkRequest(
                campaign_id="0123456789abcdef", slug="BAD SLUG", target_url="https://ok.example/x"
            )
        )

    assert caught.value.code == "invalid_slug"
    assert policy.checked == []


def test_add_link_refuses_a_campaign_that_does_not_exist() -> None:
    store = FakeCampaignStore()
    svc = service.CampaignService(store, FakeTargetPolicyAllowing(), FakeCampaignIdentity(), store)

    with pytest.raises(DomainError) as caught:
        svc.add_link(
            client.AddLinkRequest(
                campaign_id="0123456789abcdef", slug="promo", target_url="https://ok.example/x"
            )
        )

    assert caught.value.kind is Kind.NOT_FOUND
    assert caught.value.code == "campaign_missing"


def test_deactivate_link_leaves_the_link_inactive_for_later_readers() -> None:
    store = FakeCampaignStore()
    svc = service.CampaignService(store, FakeTargetPolicyAllowing(), FakeCampaignIdentity(), store)
    created = svc.create_campaign(
        client.CreateCampaignRequest(budget_amount="100.00", budget_currency="USD")
    )
    svc.add_link(
        client.AddLinkRequest(
            campaign_id=created.campaign_id, slug="promo", target_url="https://ok.example/x"
        )
    )

    svc.deactivate_link(
        client.DeactivateLinkRequest(campaign_id=created.campaign_id, slug="promo")
    )

    reread = svc.get_campaign(client.GetCampaignRequest(campaign_id=created.campaign_id))
    assert [link.status for link in reread.links] == ["inactive"]


def test_deactivate_link_refuses_a_slug_the_campaign_does_not_carry() -> None:
    store = FakeCampaignStore()
    svc = service.CampaignService(store, FakeTargetPolicyAllowing(), FakeCampaignIdentity(), store)
    created = svc.create_campaign(
        client.CreateCampaignRequest(budget_amount="100.00", budget_currency="USD")
    )

    with pytest.raises(DomainError) as caught:
        svc.deactivate_link(
            client.DeactivateLinkRequest(campaign_id=created.campaign_id, slug="nosuch")
        )

    assert caught.value.kind is Kind.NOT_FOUND
    assert caught.value.code == "link_missing"


def test_get_campaign_returns_the_budget_it_was_created_with() -> None:
    store = FakeCampaignStore()
    svc = service.CampaignService(store, FakeTargetPolicyAllowing(), FakeCampaignIdentity(), store)
    created = svc.create_campaign(
        client.CreateCampaignRequest(budget_amount="99.95", budget_currency="GBP")
    )

    view = svc.get_campaign(client.GetCampaignRequest(campaign_id=created.campaign_id))

    assert view.campaign_id == created.campaign_id
    assert view.budget_amount == "99.95"
    assert view.budget_currency == "GBP"


def test_get_campaign_refuses_a_campaign_that_does_not_exist() -> None:
    store = FakeCampaignStore()
    svc = service.CampaignService(store, FakeTargetPolicyAllowing(), FakeCampaignIdentity(), store)

    with pytest.raises(DomainError) as caught:
        svc.get_campaign(client.GetCampaignRequest(campaign_id="0123456789abcdef"))

    assert caught.value.kind is Kind.NOT_FOUND
    assert caught.value.code == "campaign_missing"


def test_resolve_hands_back_the_target_of_an_active_link() -> None:
    store = FakeCampaignStore()
    svc = service.CampaignService(store, FakeTargetPolicyAllowing(), FakeCampaignIdentity(), store)
    created = svc.create_campaign(
        client.CreateCampaignRequest(budget_amount="100.00", budget_currency="USD")
    )
    svc.add_link(
        client.AddLinkRequest(
            campaign_id=created.campaign_id, slug="promo", target_url="https://ok.example/x"
        )
    )

    resolved = svc.resolve(client.ResolveRequest(slug="promo"))

    assert resolved.target_url == "https://ok.example/x"


def test_resolve_refuses_a_slug_nobody_registered() -> None:
    store = FakeCampaignStore()
    svc = service.CampaignService(store, FakeTargetPolicyAllowing(), FakeCampaignIdentity(), store)

    with pytest.raises(DomainError) as caught:
        svc.resolve(client.ResolveRequest(slug="nosuch"))

    assert caught.value.kind is Kind.NOT_FOUND
    assert caught.value.code == "link_missing"


def test_resolve_refuses_a_malformed_slug() -> None:
    store = FakeCampaignStore()
    svc = service.CampaignService(store, FakeTargetPolicyAllowing(), FakeCampaignIdentity(), store)

    with pytest.raises(DomainError) as caught:
        svc.resolve(client.ResolveRequest(slug="BAD SLUG"))

    assert caught.value.code == "invalid_slug"


def test_list_links_gathers_the_links_of_every_campaign() -> None:
    store = FakeCampaignStore()
    svc = service.CampaignService(store, FakeTargetPolicyAllowing(), FakeCampaignIdentity(), store)
    first = svc.create_campaign(
        client.CreateCampaignRequest(budget_amount="100.00", budget_currency="USD")
    )
    second = svc.create_campaign(
        client.CreateCampaignRequest(budget_amount="100.00", budget_currency="USD")
    )
    svc.add_link(
        client.AddLinkRequest(
            campaign_id=first.campaign_id, slug="promo", target_url="https://ok.example/x"
        )
    )
    svc.add_link(
        client.AddLinkRequest(
            campaign_id=second.campaign_id, slug="sale", target_url="https://ok.example/y"
        )
    )

    listed = svc.list_links(client.ListLinksRequest())

    assert sorted(link.slug for link in listed.links) == ["promo", "sale"]


def test_list_links_reports_a_deactivated_link_as_inactive() -> None:
    store = FakeCampaignStore()
    svc = service.CampaignService(store, FakeTargetPolicyAllowing(), FakeCampaignIdentity(), store)
    created = svc.create_campaign(
        client.CreateCampaignRequest(budget_amount="100.00", budget_currency="USD")
    )
    svc.add_link(
        client.AddLinkRequest(
            campaign_id=created.campaign_id, slug="promo", target_url="https://ok.example/x"
        )
    )
    svc.deactivate_link(
        client.DeactivateLinkRequest(campaign_id=created.campaign_id, slug="promo")
    )

    listed = svc.list_links(client.ListLinksRequest())

    assert [(link.slug, link.status) for link in listed.links] == [("promo", "inactive")]


def test_list_links_is_empty_before_anything_is_created() -> None:
    store = FakeCampaignStore()
    svc = service.CampaignService(store, FakeTargetPolicyAllowing(), FakeCampaignIdentity(), store)

    assert svc.list_links(client.ListLinksRequest()).links == ()


def test_the_campaign_view_mapper_exposes_what_it_was_given() -> None:
    request = campaign_queries.FindCampaignViewRequest(campaign_id="0123456789abcdef")
    found = campaign_queries.FindCampaignViewResponse(
        outcome=campaign_queries.CampaignViewLookup.FOUND,
        campaigns=(campaign_queries.CampaignViewRow(
            campaign_id="0123456789abcdef",
            budget_amount="10.00",
            budget_currency="USD",
            links=(campaign_queries.LinkViewRow(
                slug="promo", target_url="https://ok.example/x", status="inactive"
            ),),
        ),),
    )
    mapper = service.MapToCampaignView(
        find_campaign_view_request=request, found_campaign_view=found
    )
    assert mapper.find_campaign_view_request is request
    assert mapper.found_campaign_view is found


def test_the_campaign_view_mapper_copies_the_row_into_the_view() -> None:
    mapper = service.MapToCampaignView(
        find_campaign_view_request=campaign_queries.FindCampaignViewRequest(
            campaign_id="0123456789abcdef"
        ),
        found_campaign_view=campaign_queries.FindCampaignViewResponse(
            outcome=campaign_queries.CampaignViewLookup.FOUND,
            campaigns=(campaign_queries.CampaignViewRow(
                campaign_id="0123456789abcdef",
                budget_amount="10.00",
                budget_currency="USD",
                links=(campaign_queries.LinkViewRow(
                    slug="promo", target_url="https://ok.example/x", status="inactive"
                ),),
            ),),
        ),
    )
    assert mapper.campaign_id == "0123456789abcdef"
    assert mapper.budget_amount == "10.00"
    assert mapper.budget_currency == "USD"
    assert [link.slug for link in mapper.link_views] == ["promo"]
    assert [link.status for link in mapper.link_views] == ["inactive"]


def test_the_campaign_view_mapper_refuses_a_missing_campaign() -> None:
    with pytest.raises(DomainError) as caught:
        service.MapToCampaignView(
            find_campaign_view_request=campaign_queries.FindCampaignViewRequest(
                campaign_id="0123456789abcdef"
            ),
            found_campaign_view=campaign_queries.FindCampaignViewResponse(
                outcome=campaign_queries.CampaignViewLookup.MISSING, campaigns=()
            ),
        )
    assert caught.value.code == "campaign_missing"


def test_the_save_request_mapper_exposes_the_aggregate_it_was_given() -> None:
    aggregate = campaign.Campaign(campaign.CampaignSpec(
        id="0123456789abcdef",
        budget=money.MoneySpec(amount="10.00", currency="USD"),
        links=short_links.ShortLinksSpec(links=()),
    ))
    mapper = service.MapToSaveCampaignRequest(campaign_aggregate=aggregate)
    assert mapper.campaign_aggregate is aggregate


def test_the_save_request_mapper_stringifies_the_aggregate_into_records() -> None:
    aggregate = campaign.Campaign(campaign.CampaignSpec(
        id="0123456789abcdef",
        budget=money.MoneySpec(amount="10.00", currency="USD"),
        links=short_links.ShortLinksSpec(links=(
            short_link.ShortLinkSpec(slug="promo", target_url="https://ok.example/x", active=True),
            short_link.ShortLinkSpec(slug="old", target_url="https://ok.example/y", active=False),
        )),
    ))
    mapper = service.MapToSaveCampaignRequest(campaign_aggregate=aggregate)
    assert mapper.record_id == "0123456789abcdef"
    assert mapper.money_record_mapper.amount == "10.00"
    assert mapper.money_record_mapper.currency == "USD"
    assert [record.slug for record in mapper.link_records] == ["promo", "old"]
    assert [record.status for record in mapper.link_records] == ["active", "inactive"]


def test_the_save_request_mapper_maps_no_links_to_no_records() -> None:
    aggregate = campaign.Campaign(campaign.CampaignSpec(
        id="0123456789abcdef",
        budget=money.MoneySpec(amount="10.00", currency="USD"),
        links=short_links.ShortLinksSpec(links=()),
    ))
    mapper = service.MapToSaveCampaignRequest(campaign_aggregate=aggregate)
    assert mapper.link_records == ()


def test_the_campaign_spec_mapper_exposes_what_it_was_given() -> None:
    request = client.CreateCampaignRequest(budget_amount="10.00", budget_currency="USD")
    issued = campaign_identity.IssueCampaignIdentityResponse(campaign_id="0123456789abcdef")
    given = short_links.ShortLinksSpec(
        links=(short_link.ShortLinkSpec(slug="promo", target_url="https://ok.example/x", active=True),)
    )
    mapper = service.MapToCampaignSpec(
        create_campaign_request=request,
        issued_campaign_identity=issued,
        links=given,
    )
    assert mapper.create_campaign_request is request
    assert mapper.issued_campaign_identity is issued
    assert mapper.links is given


def test_the_campaign_spec_mapper_takes_the_id_from_the_issued_identity() -> None:
    mapper = service.MapToCampaignSpec(
        create_campaign_request=client.CreateCampaignRequest(
            budget_amount="10.00", budget_currency="USD"
        ),
        issued_campaign_identity=campaign_identity.IssueCampaignIdentityResponse(
            campaign_id="0123456789abcdef"
        ),
        links=short_links.ShortLinksSpec(links=()),
    )
    assert mapper.campaign_id == "0123456789abcdef"


def test_the_nested_budget_mapper_takes_the_money_parts_from_the_request() -> None:
    request = client.CreateCampaignRequest(budget_amount="10.00", budget_currency="USD")
    mapper = service.MapToCampaignSpec(
        create_campaign_request=request,
        issued_campaign_identity=campaign_identity.IssueCampaignIdentityResponse(
            campaign_id="0123456789abcdef"
        ),
        links=short_links.ShortLinksSpec(links=()),
    )
    assert mapper.budget_mapper.create_campaign_request is request
    assert mapper.budget_mapper.amount == "10.00"
    assert mapper.budget_mapper.currency == "USD"
