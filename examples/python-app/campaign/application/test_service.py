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
import tesser.errors as errors


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
        raise errors.InfraError("linkpolicy unavailable")


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

    with pytest.raises(errors.DomainError) as caught:
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

    with pytest.raises(errors.DomainError) as caught:
        svc.add_link(
            client.AddLinkRequest(
                campaign_id=created.campaign_id, slug="promo", target_url="https://bad.example/x"
            )
        )

    assert caught.value.kind is errors.Kind.CONFLICT
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

    with pytest.raises(errors.InfraError):
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

    with pytest.raises(errors.DomainError) as caught:
        svc.add_link(
            client.AddLinkRequest(
                campaign_id=second.campaign_id, slug="promo", target_url="https://ok.example/y"
            )
        )

    assert caught.value.kind is errors.Kind.CONFLICT
    assert caught.value.code == "duplicate_slug"


def test_add_link_refuses_a_malformed_slug_without_touching_the_policy() -> None:
    policy = FakeTargetPolicyAllowing()
    store = FakeCampaignStore()
    svc = service.CampaignService(store, policy, FakeCampaignIdentity(), store)

    with pytest.raises(errors.DomainError) as caught:
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

    with pytest.raises(errors.DomainError) as caught:
        svc.add_link(
            client.AddLinkRequest(
                campaign_id="0123456789abcdef", slug="promo", target_url="https://ok.example/x"
            )
        )

    assert caught.value.kind is errors.Kind.NOT_FOUND
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

    with pytest.raises(errors.DomainError) as caught:
        svc.deactivate_link(
            client.DeactivateLinkRequest(campaign_id=created.campaign_id, slug="nosuch")
        )

    assert caught.value.kind is errors.Kind.NOT_FOUND
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

    with pytest.raises(errors.DomainError) as caught:
        svc.get_campaign(client.GetCampaignRequest(campaign_id="0123456789abcdef"))

    assert caught.value.kind is errors.Kind.NOT_FOUND
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

    with pytest.raises(errors.DomainError) as caught:
        svc.resolve(client.ResolveRequest(slug="nosuch"))

    assert caught.value.kind is errors.Kind.NOT_FOUND
    assert caught.value.code == "link_missing"


def test_resolve_refuses_a_malformed_slug() -> None:
    store = FakeCampaignStore()
    svc = service.CampaignService(store, FakeTargetPolicyAllowing(), FakeCampaignIdentity(), store)

    with pytest.raises(errors.DomainError) as caught:
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


@ts.helper
def _found_campaign_view(
    campaign_id: str = "0123456789abcdef",
    budget_amount: str = "10.00",
    budget_currency: str = "USD",
    slug: str = "promo",
    target_url: str = "https://ok.example/x",
    status: str = "inactive",
) -> campaign_queries.FindCampaignViewResponse:
    return campaign_queries.FindCampaignViewResponse(
        outcome=campaign_queries.CampaignViewLookup.FOUND,
        campaigns=(campaign_queries.CampaignViewRow(
            campaign_id=campaign_id,
            budget_amount=budget_amount,
            budget_currency=budget_currency,
            links=(campaign_queries.LinkViewRow(
                slug=slug, target_url=target_url, status=status
            ),),
        ),),
    )


@ts.helper
def _missing_campaign_view() -> campaign_queries.FindCampaignViewResponse:
    return campaign_queries.FindCampaignViewResponse(
        outcome=campaign_queries.CampaignViewLookup.MISSING, campaigns=()
    )


def test_the_campaign_view_mapper_is_the_view_built_from_the_row() -> None:
    view = service.MapToCampaignView(
        find_campaign_view_request=campaign_queries.FindCampaignViewRequest(
            campaign_id="0123456789abcdef"
        ),
        found_campaign_view=_found_campaign_view(),
    )
    assert isinstance(view, client.CampaignView)
    assert view.campaign_id == "0123456789abcdef"
    assert view.budget_amount == "10.00"
    assert view.budget_currency == "USD"
    assert [link.slug for link in view.links] == ["promo"]
    assert [link.status for link in view.links] == ["inactive"]


def test_the_link_view_mapper_is_the_view_built_from_the_row() -> None:
    view = service.MapToLinkView(link_row=campaign_queries.LinkViewRow(
        slug="promo", target_url="https://ok.example/x", status="inactive"
    ))
    assert isinstance(view, client.LinkView)
    assert (view.slug, view.target_url, view.status) == (
        "promo", "https://ok.example/x", "inactive"
    )


def test_the_campaign_view_mapper_refuses_a_missing_campaign() -> None:
    with pytest.raises(errors.DomainError) as caught:
        service.MapToCampaignView(
            find_campaign_view_request=campaign_queries.FindCampaignViewRequest(
                campaign_id="0123456789abcdef"
            ),
            found_campaign_view=_missing_campaign_view(),
        )
    assert caught.value.code == "campaign_missing"


def test_the_save_request_mapper_stringifies_the_aggregate_into_the_request() -> None:
    aggregate = campaign.Campaign(campaign.CampaignSpec(
        id="0123456789abcdef",
        budget=money.MoneySpec(amount="10.00", currency="USD"),
        links=short_links.ShortLinksSpec(links=(
            short_link.ShortLinkSpec(slug="promo", target_url="https://ok.example/x", active=True),
            short_link.ShortLinkSpec(slug="old", target_url="https://ok.example/y", active=False),
        )),
    ))
    save_request = service.MapToSaveCampaignRequest(campaign_aggregate=aggregate)
    assert isinstance(save_request, campaign_repository.SaveCampaignRequest)
    assert save_request.id == "0123456789abcdef"
    assert save_request.budget.amount == "10.00"
    assert save_request.budget.currency == "USD"
    assert [record.slug for record in save_request.links] == ["promo", "old"]
    assert [record.status for record in save_request.links] == ["active", "inactive"]


def test_the_save_request_mapper_maps_no_links_to_no_records() -> None:
    aggregate = campaign.Campaign(campaign.CampaignSpec(
        id="0123456789abcdef",
        budget=money.MoneySpec(amount="10.00", currency="USD"),
        links=short_links.ShortLinksSpec(links=()),
    ))
    save_request = service.MapToSaveCampaignRequest(campaign_aggregate=aggregate)
    assert save_request.links == ()


def test_the_campaign_spec_mapper_takes_the_id_from_the_issued_identity_and_the_links_whole() -> None:
    given = short_links.ShortLinksSpec(
        links=(short_link.ShortLinkSpec(slug="promo", target_url="https://ok.example/x", active=True),)
    )
    spec = service.MapToCampaignSpec(
        create_campaign_request=client.CreateCampaignRequest(
            budget_amount="10.00", budget_currency="USD"
        ),
        issued_campaign_identity=campaign_identity.IssueCampaignIdentityResponse(
            campaign_id="0123456789abcdef"
        ),
        links=given,
    )
    assert isinstance(spec, campaign.CampaignSpec)
    assert spec.id == "0123456789abcdef"
    assert spec.links is given


def test_the_campaign_spec_mapper_nests_the_money_spec_from_the_request() -> None:
    spec = service.MapToCampaignSpec(
        create_campaign_request=client.CreateCampaignRequest(
            budget_amount="10.00", budget_currency="USD"
        ),
        issued_campaign_identity=campaign_identity.IssueCampaignIdentityResponse(
            campaign_id="0123456789abcdef"
        ),
        links=short_links.ShortLinksSpec(links=()),
    )
    assert isinstance(spec.budget, money.MoneySpec)
    assert spec.budget.amount == "10.00"
    assert spec.budget.currency == "USD"
    assert str(campaign.Campaign(spec).budget.amount) == "10.00"


def test_the_link_record_mapper_stringifies_the_entity() -> None:
    entity = short_link.ShortLink(short_link.ShortLinkSpec(
        slug="promo", target_url="https://ok.example/x", active=True
    ))
    record = service.MapToLinkRecord(short_link_entity=entity)
    assert isinstance(record, campaign_repository.LinkRecord)
    assert record.slug == "promo"
    assert record.target_url == "https://ok.example/x"
    assert record.status == "active"


def test_the_campaign_spec_mapper_from_a_record_rebuilds_the_links_it_was_given() -> None:
    find_campaign_request = campaign_repository.FindCampaignRequest(campaign_id="0123456789abcdef")
    record = campaign_repository.CampaignRecord(
        id="0123456789abcdef",
        budget=campaign_repository.MoneyRecord(amount="10.00", currency="USD"),
        links=(campaign_repository.LinkRecord(
            slug="promo", target_url="https://ok.example/x", status="inactive"
        ),),
    )
    found_campaign = campaign_repository.FindCampaignResponse(
        outcome=campaign_repository.CampaignLookup.FOUND, campaigns=(record,)
    )
    spec = service.MapToCampaignSpecFromRecord(
        find_campaign_request=find_campaign_request, found_campaign=found_campaign
    )
    assert isinstance(spec, campaign.CampaignSpec)
    assert spec.id == "0123456789abcdef"
    assert (spec.budget.amount, spec.budget.currency) == ("10.00", "USD")
    assert [(link.slug, link.active) for link in spec.links.links] == [("promo", False)]


def test_deactivate_link_refuses_a_malformed_campaign_id_before_the_repository_is_touched() -> None:
    store = FakeCampaignStore()
    svc = service.CampaignService(store, FakeTargetPolicyAllowing(), FakeCampaignIdentity(), store)
    with pytest.raises(errors.DomainError) as caught:
        svc.deactivate_link(client.DeactivateLinkRequest(campaign_id="not-hex", slug="promo"))
    assert caught.value.kind is errors.Kind.VALIDATION
    assert caught.value.code == "invalid_campaign_id"
    assert store.saved == []
