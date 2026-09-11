from __future__ import annotations

import pytest
import tesser.testing as ts

import campaign.application as application
import campaign.application.ports as ports
import campaign.client as client
import campaign.domain as domain


@ts.fake
class FakeCampaignStore(ports.CampaignRepository):

    def __init__(self) -> None:
        self.rows: dict[str, ports.CampaignRecord] = {}
        self.saved: list[ports.SaveCampaignRequest] = []

    def save(
        self, save_campaign_request: ports.SaveCampaignRequest
    ) -> ports.SaveCampaignResponse:
        self.saved.append(save_campaign_request)
        self.rows[save_campaign_request.id] = ports.CampaignRecord(
            id=save_campaign_request.id, budget=save_campaign_request.budget, links=save_campaign_request.links
        )
        return ports.SaveCampaignResponse()

    def find(
        self, find_campaign_request: ports.FindCampaignRequest
    ) -> ports.FindCampaignResponse:
        row = self.rows.get(find_campaign_request.campaign_id)
        if row is None:
            return ports.FindCampaignResponse(
                outcome=ports.CampaignLookup.MISSING, campaigns=()
            )
        return ports.FindCampaignResponse(
            outcome=ports.CampaignLookup.FOUND, campaigns=(row,)
        )

    def find_by_slug(
        self, find_campaign_by_slug_request: ports.FindCampaignBySlugRequest
    ) -> ports.FindCampaignResponse:
        for row in self.rows.values():
            if any(link.slug == find_campaign_by_slug_request.slug for link in row.links):
                return ports.FindCampaignResponse(
                    outcome=ports.CampaignLookup.FOUND, campaigns=(row,)
                )
        return ports.FindCampaignResponse(
            outcome=ports.CampaignLookup.MISSING, campaigns=()
        )

    def slug_taken(
        self, slug_taken_request: ports.SlugTakenRequest
    ) -> ports.SlugTakenResponse:
        taken = any(
            link.slug == slug_taken_request.slug for row in self.rows.values() for link in row.links
        )
        return ports.SlugTakenResponse(
            availability=ports.SlugAvailability.TAKEN
            if taken
            else ports.SlugAvailability.FREE
        )

    def all(
        self, list_campaigns_request: ports.ListCampaignsRequest
    ) -> ports.ListCampaignsResponse:
        return ports.ListCampaignsResponse(campaigns=tuple(self.rows.values()))

    def find_view(
        self, find_campaign_view_request: ports.FindCampaignViewRequest
    ) -> ports.FindCampaignViewResponse:
        row = self.rows.get(find_campaign_view_request.campaign_id)
        if row is None:
            return ports.FindCampaignViewResponse(
                outcome=ports.CampaignViewLookup.MISSING, campaigns=()
            )
        links: list[ports.LinkViewRow] = []
        for link in row.links:
            links.append(ports.LinkViewRow(
                slug=link.slug, target_url=link.target_url, status=link.status
            ))
        campaign_view_row = ports.CampaignViewRow(
            campaign_id=row.id,
            budget_amount=row.budget.amount,
            budget_currency=row.budget.currency,
            links=tuple(links),
        )
        return ports.FindCampaignViewResponse(
            outcome=ports.CampaignViewLookup.FOUND, campaigns=(campaign_view_row,)
        )


@ts.fake
class FakeCampaignIdentity(ports.CampaignIdentity):

    def __init__(self) -> None:
        self.issued = 0

    def issue(
        self, issue_campaign_identity_request: ports.IssueCampaignIdentityRequest
    ) -> ports.IssueCampaignIdentityResponse:
        self.issued += 1
        campaign_id = f"{self.issued:016x}"
        return ports.IssueCampaignIdentityResponse(campaign_id=campaign_id)


@ts.fake
class FakeTargetPolicyAllowing(ports.TargetPolicy):

    def __init__(self) -> None:
        self.checked: list[str] = []

    def check(
        self, check_target_request: ports.CheckTargetRequest
    ) -> ports.CheckTargetResponse:
        self.checked.append(check_target_request.target_url)
        return ports.CheckTargetResponse(
            verdict=ports.PolicyVerdict.ALLOWED, reason="clean"
        )


@ts.fake
class FakeTargetPolicyBlocking(ports.TargetPolicy):

    def check(
        self, check_target_request: ports.CheckTargetRequest
    ) -> ports.CheckTargetResponse:
        return ports.CheckTargetResponse(
            verdict=ports.PolicyVerdict.BLOCKED, reason="on the deny-list"
        )


@ts.fake
class FakeTargetPolicyDown(ports.TargetPolicy):

    def check(
        self, check_target_request: ports.CheckTargetRequest
    ) -> ports.CheckTargetResponse:
        raise ports.PolicyUnavailable("linkpolicy unavailable")


def test_create_campaign_returns_the_budget_it_was_asked_for() -> None:
    fake_campaign_store = FakeCampaignStore()
    campaign_service = application.CampaignService(fake_campaign_store, FakeTargetPolicyAllowing(), FakeCampaignIdentity(), fake_campaign_store)

    campaign_view = campaign_service.create_campaign(
        client.CreateCampaignRequest(budget_amount="250.00", budget_currency="EUR")
    )

    assert campaign_view.budget_amount == "250.00"
    assert campaign_view.budget_currency == "EUR"
    assert campaign_view.links == ()


def test_create_campaign_persists_the_campaign_it_returns() -> None:
    fake_campaign_store = FakeCampaignStore()
    campaign_service = application.CampaignService(fake_campaign_store, FakeTargetPolicyAllowing(), FakeCampaignIdentity(), fake_campaign_store)

    campaign_view = campaign_service.create_campaign(
        client.CreateCampaignRequest(budget_amount="100.00", budget_currency="USD")
    )

    assert [saved.id for saved in fake_campaign_store.saved] == [campaign_view.campaign_id]


def test_create_campaign_mints_a_distinct_id_per_campaign() -> None:
    fake_campaign_store = FakeCampaignStore()
    campaign_service = application.CampaignService(fake_campaign_store, FakeTargetPolicyAllowing(), FakeCampaignIdentity(), fake_campaign_store)

    first = campaign_service.create_campaign(
        client.CreateCampaignRequest(budget_amount="100.00", budget_currency="USD")
    )
    second = campaign_service.create_campaign(
        client.CreateCampaignRequest(budget_amount="100.00", budget_currency="USD")
    )

    assert first.campaign_id != second.campaign_id


def test_create_campaign_refuses_a_malformed_currency_and_saves_nothing() -> None:
    fake_campaign_store = FakeCampaignStore()
    campaign_service = application.CampaignService(fake_campaign_store, FakeTargetPolicyAllowing(), FakeCampaignIdentity(), fake_campaign_store)

    with pytest.raises(client.Rejected) as caught:
        campaign_service.create_campaign(
            client.CreateCampaignRequest(budget_amount="100.00", budget_currency="dollars")
        )

    assert caught.value.code == "invalid_budget_currency"
    assert fake_campaign_store.saved == []


def test_add_link_puts_the_link_on_the_campaign() -> None:
    fake_campaign_store = FakeCampaignStore()
    campaign_service = application.CampaignService(fake_campaign_store, FakeTargetPolicyAllowing(), FakeCampaignIdentity(), fake_campaign_store)
    created = campaign_service.create_campaign(
        client.CreateCampaignRequest(budget_amount="100.00", budget_currency="USD")
    )

    view = campaign_service.add_link(
        client.AddLinkRequest(
            campaign_id=created.campaign_id, slug="promo", target_url="https://ok.example/x"
        )
    )

    assert [(link.slug, link.target_url, link.status) for link in view.links] == [
        ("promo", "https://ok.example/x", "active")
    ]


def test_add_link_asks_the_policy_about_the_target_before_admitting_it() -> None:
    fake_target_policy_allowing = FakeTargetPolicyAllowing()
    fake_campaign_store = FakeCampaignStore()
    campaign_service = application.CampaignService(fake_campaign_store, fake_target_policy_allowing, FakeCampaignIdentity(), fake_campaign_store)
    campaign_view = campaign_service.create_campaign(
        client.CreateCampaignRequest(budget_amount="100.00", budget_currency="USD")
    )

    campaign_service.add_link(
        client.AddLinkRequest(
            campaign_id=campaign_view.campaign_id, slug="promo", target_url="https://ok.example/x"
        )
    )

    assert fake_target_policy_allowing.checked == ["https://ok.example/x"]


def test_add_link_refuses_a_blocked_destination_and_saves_nothing() -> None:
    fake_campaign_store = FakeCampaignStore()
    allowing = application.CampaignService(fake_campaign_store, FakeTargetPolicyAllowing(), FakeCampaignIdentity(), fake_campaign_store)
    campaign_view = allowing.create_campaign(
        client.CreateCampaignRequest(budget_amount="100.00", budget_currency="USD")
    )
    campaign_service = application.CampaignService(fake_campaign_store, FakeTargetPolicyBlocking(), FakeCampaignIdentity(), fake_campaign_store)
    before = len(fake_campaign_store.saved)

    with pytest.raises(client.Conflict) as caught:
        campaign_service.add_link(
            client.AddLinkRequest(
                campaign_id=campaign_view.campaign_id, slug="promo", target_url="https://bad.example/x"
            )
        )

    assert caught.value.code == "destination_blocked"
    assert "on the deny-list" in caught.value.message
    assert len(fake_campaign_store.saved) == before


def test_add_link_lets_a_policy_outage_surface_and_saves_nothing() -> None:
    fake_campaign_store = FakeCampaignStore()
    allowing = application.CampaignService(fake_campaign_store, FakeTargetPolicyAllowing(), FakeCampaignIdentity(), fake_campaign_store)
    campaign_view = allowing.create_campaign(
        client.CreateCampaignRequest(budget_amount="100.00", budget_currency="USD")
    )
    campaign_service = application.CampaignService(fake_campaign_store, FakeTargetPolicyDown(), FakeCampaignIdentity(), fake_campaign_store)
    before = len(fake_campaign_store.saved)

    with pytest.raises(ports.PolicyUnavailable):
        campaign_service.add_link(
            client.AddLinkRequest(
                campaign_id=campaign_view.campaign_id, slug="promo", target_url="https://ok.example/x"
            )
        )

    assert len(fake_campaign_store.saved) == before


def test_add_link_refuses_a_slug_another_campaign_already_uses() -> None:
    fake_campaign_store = FakeCampaignStore()
    campaign_service = application.CampaignService(fake_campaign_store, FakeTargetPolicyAllowing(), FakeCampaignIdentity(), fake_campaign_store)
    first = campaign_service.create_campaign(
        client.CreateCampaignRequest(budget_amount="100.00", budget_currency="USD")
    )
    second = campaign_service.create_campaign(
        client.CreateCampaignRequest(budget_amount="100.00", budget_currency="USD")
    )
    campaign_service.add_link(
        client.AddLinkRequest(
            campaign_id=first.campaign_id, slug="promo", target_url="https://ok.example/x"
        )
    )

    with pytest.raises(client.Conflict) as caught:
        campaign_service.add_link(
            client.AddLinkRequest(
                campaign_id=second.campaign_id, slug="promo", target_url="https://ok.example/y"
            )
        )

    assert caught.value.code == "duplicate_slug"


def test_add_link_refuses_a_malformed_slug_without_touching_the_policy() -> None:
    fake_target_policy_allowing = FakeTargetPolicyAllowing()
    fake_campaign_store = FakeCampaignStore()
    campaign_service = application.CampaignService(fake_campaign_store, fake_target_policy_allowing, FakeCampaignIdentity(), fake_campaign_store)

    with pytest.raises(client.Rejected) as caught:
        campaign_service.add_link(
            client.AddLinkRequest(
                campaign_id="0123456789abcdef", slug="BAD SLUG", target_url="https://ok.example/x"
            )
        )

    assert caught.value.code == "invalid_slug"
    assert fake_target_policy_allowing.checked == []


def test_add_link_refuses_a_campaign_that_does_not_exist() -> None:
    fake_campaign_store = FakeCampaignStore()
    campaign_service = application.CampaignService(fake_campaign_store, FakeTargetPolicyAllowing(), FakeCampaignIdentity(), fake_campaign_store)

    with pytest.raises(client.Missing) as caught:
        campaign_service.add_link(
            client.AddLinkRequest(
                campaign_id="0123456789abcdef", slug="promo", target_url="https://ok.example/x"
            )
        )

    assert caught.value.code == "campaign_missing"


def test_deactivate_link_leaves_the_link_inactive_for_later_readers() -> None:
    fake_campaign_store = FakeCampaignStore()
    campaign_service = application.CampaignService(fake_campaign_store, FakeTargetPolicyAllowing(), FakeCampaignIdentity(), fake_campaign_store)
    created = campaign_service.create_campaign(
        client.CreateCampaignRequest(budget_amount="100.00", budget_currency="USD")
    )
    campaign_service.add_link(
        client.AddLinkRequest(
            campaign_id=created.campaign_id, slug="promo", target_url="https://ok.example/x"
        )
    )

    campaign_service.deactivate_link(
        client.DeactivateLinkRequest(campaign_id=created.campaign_id, slug="promo")
    )

    reread = campaign_service.get_campaign(client.GetCampaignRequest(campaign_id=created.campaign_id))
    assert [link.status for link in reread.links] == ["inactive"]


def test_deactivate_link_refuses_a_slug_the_campaign_does_not_carry() -> None:
    fake_campaign_store = FakeCampaignStore()
    campaign_service = application.CampaignService(fake_campaign_store, FakeTargetPolicyAllowing(), FakeCampaignIdentity(), fake_campaign_store)
    campaign_view = campaign_service.create_campaign(
        client.CreateCampaignRequest(budget_amount="100.00", budget_currency="USD")
    )

    with pytest.raises(client.Missing) as caught:
        campaign_service.deactivate_link(
            client.DeactivateLinkRequest(campaign_id=campaign_view.campaign_id, slug="nosuch")
        )

    assert caught.value.code == "link_missing"


def test_get_campaign_returns_the_budget_it_was_created_with() -> None:
    fake_campaign_store = FakeCampaignStore()
    campaign_service = application.CampaignService(fake_campaign_store, FakeTargetPolicyAllowing(), FakeCampaignIdentity(), fake_campaign_store)
    created = campaign_service.create_campaign(
        client.CreateCampaignRequest(budget_amount="99.95", budget_currency="GBP")
    )

    view = campaign_service.get_campaign(client.GetCampaignRequest(campaign_id=created.campaign_id))

    assert view.campaign_id == created.campaign_id
    assert view.budget_amount == "99.95"
    assert view.budget_currency == "GBP"


def test_get_campaign_refuses_a_campaign_that_does_not_exist() -> None:
    fake_campaign_store = FakeCampaignStore()
    campaign_service = application.CampaignService(fake_campaign_store, FakeTargetPolicyAllowing(), FakeCampaignIdentity(), fake_campaign_store)

    with pytest.raises(client.Missing) as caught:
        campaign_service.get_campaign(client.GetCampaignRequest(campaign_id="0123456789abcdef"))

    assert caught.value.code == "campaign_missing"


def test_resolve_hands_back_the_target_of_an_active_link() -> None:
    fake_campaign_store = FakeCampaignStore()
    campaign_service = application.CampaignService(fake_campaign_store, FakeTargetPolicyAllowing(), FakeCampaignIdentity(), fake_campaign_store)
    campaign_view = campaign_service.create_campaign(
        client.CreateCampaignRequest(budget_amount="100.00", budget_currency="USD")
    )
    campaign_service.add_link(
        client.AddLinkRequest(
            campaign_id=campaign_view.campaign_id, slug="promo", target_url="https://ok.example/x"
        )
    )

    resolve_response = campaign_service.resolve(client.ResolveRequest(slug="promo"))

    assert resolve_response.target_url == "https://ok.example/x"


def test_resolve_refuses_a_slug_nobody_registered() -> None:
    fake_campaign_store = FakeCampaignStore()
    campaign_service = application.CampaignService(fake_campaign_store, FakeTargetPolicyAllowing(), FakeCampaignIdentity(), fake_campaign_store)

    with pytest.raises(client.Missing) as caught:
        campaign_service.resolve(client.ResolveRequest(slug="nosuch"))

    assert caught.value.code == "link_missing"


def test_resolve_refuses_a_malformed_slug() -> None:
    fake_campaign_store = FakeCampaignStore()
    campaign_service = application.CampaignService(fake_campaign_store, FakeTargetPolicyAllowing(), FakeCampaignIdentity(), fake_campaign_store)

    with pytest.raises(client.Rejected) as caught:
        campaign_service.resolve(client.ResolveRequest(slug="BAD SLUG"))

    assert caught.value.code == "invalid_slug"


def test_list_links_gathers_the_links_of_every_campaign() -> None:
    fake_campaign_store = FakeCampaignStore()
    campaign_service = application.CampaignService(fake_campaign_store, FakeTargetPolicyAllowing(), FakeCampaignIdentity(), fake_campaign_store)
    first = campaign_service.create_campaign(
        client.CreateCampaignRequest(budget_amount="100.00", budget_currency="USD")
    )
    second = campaign_service.create_campaign(
        client.CreateCampaignRequest(budget_amount="100.00", budget_currency="USD")
    )
    campaign_service.add_link(
        client.AddLinkRequest(
            campaign_id=first.campaign_id, slug="promo", target_url="https://ok.example/x"
        )
    )
    campaign_service.add_link(
        client.AddLinkRequest(
            campaign_id=second.campaign_id, slug="sale", target_url="https://ok.example/y"
        )
    )

    list_links_response = campaign_service.list_links(client.ListLinksRequest())

    assert sorted(link.slug for link in list_links_response.links) == ["promo", "sale"]


def test_list_links_reports_a_deactivated_link_as_inactive() -> None:
    fake_campaign_store = FakeCampaignStore()
    campaign_service = application.CampaignService(fake_campaign_store, FakeTargetPolicyAllowing(), FakeCampaignIdentity(), fake_campaign_store)
    campaign_view = campaign_service.create_campaign(
        client.CreateCampaignRequest(budget_amount="100.00", budget_currency="USD")
    )
    campaign_service.add_link(
        client.AddLinkRequest(
            campaign_id=campaign_view.campaign_id, slug="promo", target_url="https://ok.example/x"
        )
    )
    campaign_service.deactivate_link(
        client.DeactivateLinkRequest(campaign_id=campaign_view.campaign_id, slug="promo")
    )

    list_links_response = campaign_service.list_links(client.ListLinksRequest())

    assert [(link.slug, link.status) for link in list_links_response.links] == [("promo", "inactive")]


def test_list_links_is_empty_before_anything_is_created() -> None:
    fake_campaign_store = FakeCampaignStore()
    campaign_service = application.CampaignService(fake_campaign_store, FakeTargetPolicyAllowing(), FakeCampaignIdentity(), fake_campaign_store)

    assert campaign_service.list_links(client.ListLinksRequest()).links == ()


@ts.helper
def _found_campaign_view(
    campaign_id: str = "0123456789abcdef",
    budget_amount: str = "10.00",
    budget_currency: str = "USD",
    slug: str = "promo",
    target_url: str = "https://ok.example/x",
    status: str = "inactive",
) -> ports.FindCampaignViewResponse:
    return ports.FindCampaignViewResponse(
        outcome=ports.CampaignViewLookup.FOUND,
        campaigns=(ports.CampaignViewRow(
            campaign_id=campaign_id,
            budget_amount=budget_amount,
            budget_currency=budget_currency,
            links=(ports.LinkViewRow(
                slug=slug, target_url=target_url, status=status
            ),),
        ),),
    )


@ts.helper
def _missing_campaign_view() -> ports.FindCampaignViewResponse:
    return ports.FindCampaignViewResponse(
        outcome=ports.CampaignViewLookup.MISSING, campaigns=()
    )


def test_the_campaign_view_mapper_is_the_view_built_from_the_row() -> None:
    campaign_view = application.MapToCampaignView(
        find_campaign_view_request=ports.FindCampaignViewRequest(
            campaign_id="0123456789abcdef"
        ),
        find_campaign_view_response=_found_campaign_view(),
    )
    assert isinstance(campaign_view, client.CampaignView)
    assert campaign_view.campaign_id == "0123456789abcdef"
    assert campaign_view.budget_amount == "10.00"
    assert campaign_view.budget_currency == "USD"
    assert [link.slug for link in campaign_view.links] == ["promo"]
    assert [link.status for link in campaign_view.links] == ["inactive"]


def test_the_link_view_mapper_is_the_view_built_from_the_row() -> None:
    link_view = application.MapToLinkView(link_view_row=ports.LinkViewRow(
        slug="promo", target_url="https://ok.example/x", status="inactive"
    ))
    assert isinstance(link_view, client.LinkView)
    assert (link_view.slug, link_view.target_url, link_view.status) == (
        "promo", "https://ok.example/x", "inactive"
    )


def test_the_campaign_view_mapper_refuses_a_missing_campaign() -> None:
    with pytest.raises(client.Missing) as caught:
        application.MapToCampaignView(
            find_campaign_view_request=ports.FindCampaignViewRequest(
                campaign_id="0123456789abcdef"
            ),
            find_campaign_view_response=_missing_campaign_view(),
        )
    assert caught.value.code == "campaign_missing"


def test_the_save_request_mapper_stringifies_the_aggregate_into_the_request() -> None:
    campaign = domain.Campaign(domain.CampaignSpec(
        id="0123456789abcdef",
        budget=domain.MoneySpec(amount="10.00", currency="USD"),
        links=domain.ShortLinksSpec(links=(
            domain.ShortLinkSpec(slug="promo", target_url="https://ok.example/x", active=True),
            domain.ShortLinkSpec(slug="old", target_url="https://ok.example/y", active=False),
        )),
    ))
    save_campaign_request = application.MapToSaveCampaignRequest(campaign=campaign)
    assert isinstance(save_campaign_request, ports.SaveCampaignRequest)
    assert save_campaign_request.id == "0123456789abcdef"
    assert save_campaign_request.budget.amount == "10.00"
    assert save_campaign_request.budget.currency == "USD"
    assert [record.slug for record in save_campaign_request.links] == ["promo", "old"]
    assert [record.status for record in save_campaign_request.links] == ["active", "inactive"]


def test_the_save_request_mapper_maps_no_links_to_no_records() -> None:
    campaign = domain.Campaign(domain.CampaignSpec(
        id="0123456789abcdef",
        budget=domain.MoneySpec(amount="10.00", currency="USD"),
        links=domain.ShortLinksSpec(links=()),
    ))
    save_campaign_request = application.MapToSaveCampaignRequest(campaign=campaign)
    assert save_campaign_request.links == ()


def test_the_campaign_spec_mapper_takes_the_id_from_the_issued_identity_and_the_links_whole() -> None:
    short_links_spec = domain.ShortLinksSpec(
        links=(domain.ShortLinkSpec(slug="promo", target_url="https://ok.example/x", active=True),)
    )
    campaign_spec = application.MapToCampaignSpec(
        create_campaign_request=client.CreateCampaignRequest(
            budget_amount="10.00", budget_currency="USD"
        ),
        issue_campaign_identity_response=ports.IssueCampaignIdentityResponse(
            campaign_id="0123456789abcdef"
        ),
        short_links_spec=short_links_spec,
    )
    assert isinstance(campaign_spec, domain.CampaignSpec)
    assert campaign_spec.id == "0123456789abcdef"
    assert campaign_spec.links is short_links_spec


def test_the_campaign_spec_mapper_nests_the_money_spec_from_the_request() -> None:
    campaign_spec = application.MapToCampaignSpec(
        create_campaign_request=client.CreateCampaignRequest(
            budget_amount="10.00", budget_currency="USD"
        ),
        issue_campaign_identity_response=ports.IssueCampaignIdentityResponse(
            campaign_id="0123456789abcdef"
        ),
        short_links_spec=domain.ShortLinksSpec(links=()),
    )
    assert isinstance(campaign_spec.budget, domain.MoneySpec)
    assert campaign_spec.budget.amount == "10.00"
    assert campaign_spec.budget.currency == "USD"
    assert str(domain.Campaign(campaign_spec).budget.amount) == "10.00"


def test_the_link_record_mapper_stringifies_the_entity() -> None:
    short_link = domain.ShortLink(domain.ShortLinkSpec(
        slug="promo", target_url="https://ok.example/x", active=True
    ))
    link_record = application.MapToLinkRecord(short_link=short_link)
    assert isinstance(link_record, ports.LinkRecord)
    assert link_record.slug == "promo"
    assert link_record.target_url == "https://ok.example/x"
    assert link_record.status == "active"


def test_the_campaign_spec_mapper_from_a_record_rebuilds_the_links_it_was_given() -> None:
    find_campaign_request = ports.FindCampaignRequest(campaign_id="0123456789abcdef")
    campaign_record = ports.CampaignRecord(
        id="0123456789abcdef",
        budget=ports.MoneyRecord(amount="10.00", currency="USD"),
        links=(ports.LinkRecord(
            slug="promo", target_url="https://ok.example/x", status="inactive"
        ),),
    )
    find_campaign_response = ports.FindCampaignResponse(
        outcome=ports.CampaignLookup.FOUND, campaigns=(campaign_record,)
    )
    campaign_spec = application.MapToCampaignSpecFromRecord(
        find_campaign_request=find_campaign_request, find_campaign_response=find_campaign_response
    )
    assert isinstance(campaign_spec, domain.CampaignSpec)
    assert campaign_spec.id == "0123456789abcdef"
    assert (campaign_spec.budget.amount, campaign_spec.budget.currency) == ("10.00", "USD")
    assert [(link.slug, link.active) for link in campaign_spec.links.links] == [("promo", False)]


def test_deactivate_link_refuses_a_malformed_campaign_id_before_the_repository_is_touched() -> None:
    fake_campaign_store = FakeCampaignStore()
    campaign_service = application.CampaignService(fake_campaign_store, FakeTargetPolicyAllowing(), FakeCampaignIdentity(), fake_campaign_store)
    with pytest.raises(client.Rejected) as caught:
        campaign_service.deactivate_link(client.DeactivateLinkRequest(campaign_id="not-hex", slug="promo"))
    assert caught.value.code == "invalid_campaign_id"
    assert fake_campaign_store.saved == []



def test_a_found_slug_lookup_is_the_spec_the_campaign_is_rebuilt_from() -> None:
    find_campaign_response = ports.FindCampaignResponse(
        outcome=ports.CampaignLookup.FOUND,
        campaigns=(
            ports.CampaignRecord(
                id="0123456789abcdef",
                budget=ports.MoneyRecord(amount="100.00", currency="USD"),
                links=(
                    ports.LinkRecord(
                        slug="promo", target_url="https://ok.example/x", status="active"
                    ),
                ),
            ),
        ),
    )

    campaign_spec = application.MapToCampaignSpecFromSlugLookup(
        find_campaign_by_slug_request=ports.FindCampaignBySlugRequest(
            slug="promo"
        ),
        find_campaign_response=find_campaign_response,
    )

    assert campaign_spec.id == "0123456789abcdef"
    assert (campaign_spec.budget.amount, campaign_spec.budget.currency) == ("100.00", "USD")
    assert tuple(
        (link.slug, link.target_url, link.active) for link in campaign_spec.links.links
    ) == (("promo", "https://ok.example/x", True),)


def test_a_missing_slug_lookup_is_refused_before_anything_is_rebuilt() -> None:
    find_campaign_response = ports.FindCampaignResponse(
        outcome=ports.CampaignLookup.MISSING, campaigns=()
    )

    with pytest.raises(client.Missing) as caught:
        application.MapToCampaignSpecFromSlugLookup(
            find_campaign_by_slug_request=ports.FindCampaignBySlugRequest(
                slug="promo"
            ),
            find_campaign_response=find_campaign_response,
        )

    assert caught.value.code == "link_missing"
    assert "promo" in caught.value.message


def test_a_deactivated_link_still_reaches_the_mapper_because_the_store_does_not_judge() -> None:
    find_campaign_response = ports.FindCampaignResponse(
        outcome=ports.CampaignLookup.FOUND,
        campaigns=(
            ports.CampaignRecord(
                id="0123456789abcdef",
                budget=ports.MoneyRecord(amount="100.00", currency="USD"),
                links=(
                    ports.LinkRecord(
                        slug="promo",
                        target_url="https://ok.example/x",
                        status="inactive",
                    ),
                ),
            ),
        ),
    )

    campaign_spec = application.MapToCampaignSpecFromSlugLookup(
        find_campaign_by_slug_request=ports.FindCampaignBySlugRequest(
            slug="promo"
        ),
        find_campaign_response=find_campaign_response,
    )

    assert campaign_spec.links.links[0].active is False
