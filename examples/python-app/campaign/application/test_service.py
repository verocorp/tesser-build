from __future__ import annotations

import pytest
import tesser.testing as ts

import campaign.application.ports.campaign_repository as campaign_repository
import campaign.application.ports.target_policy as target_policy
import campaign.application.service as service
import campaign.client.client as client
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
    svc = service.CampaignService(FakeCampaignStore(), FakeTargetPolicyAllowing())

    view = svc.create_campaign(
        client.CreateCampaignRequest(budget_amount="250.00", budget_currency="EUR")
    )

    assert view.budget_amount == "250.00"
    assert view.budget_currency == "EUR"
    assert view.links == ()


def test_create_campaign_persists_the_campaign_it_returns() -> None:
    repo = FakeCampaignStore()
    svc = service.CampaignService(repo, FakeTargetPolicyAllowing())

    view = svc.create_campaign(
        client.CreateCampaignRequest(budget_amount="100.00", budget_currency="USD")
    )

    assert [saved.id for saved in repo.saved] == [view.campaign_id]


def test_create_campaign_mints_a_distinct_id_per_campaign() -> None:
    svc = service.CampaignService(FakeCampaignStore(), FakeTargetPolicyAllowing())

    first = svc.create_campaign(
        client.CreateCampaignRequest(budget_amount="100.00", budget_currency="USD")
    )
    second = svc.create_campaign(
        client.CreateCampaignRequest(budget_amount="100.00", budget_currency="USD")
    )

    assert first.campaign_id != second.campaign_id


def test_create_campaign_refuses_a_malformed_currency_and_saves_nothing() -> None:
    repo = FakeCampaignStore()
    svc = service.CampaignService(repo, FakeTargetPolicyAllowing())

    with pytest.raises(DomainError) as caught:
        svc.create_campaign(
            client.CreateCampaignRequest(budget_amount="100.00", budget_currency="dollars")
        )

    assert caught.value.code == "invalid_budget_currency"
    assert repo.saved == []


def test_add_link_puts_the_link_on_the_campaign() -> None:
    repo = FakeCampaignStore()
    svc = service.CampaignService(repo, FakeTargetPolicyAllowing())
    created = svc.create_campaign(
        client.CreateCampaignRequest(budget_amount="100.00", budget_currency="USD")
    )

    view = svc.add_link(
        client.AddLinkRequest(
            campaign_id=created.campaign_id, slug="promo", target_url="https://ok.example/x"
        )
    )

    assert [(link.slug, link.target_url, link.active) for link in view.links] == [
        ("promo", "https://ok.example/x", True)
    ]


def test_add_link_asks_the_policy_about_the_target_before_admitting_it() -> None:
    policy = FakeTargetPolicyAllowing()
    svc = service.CampaignService(FakeCampaignStore(), policy)
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
    allowing = service.CampaignService(repo, FakeTargetPolicyAllowing())
    created = allowing.create_campaign(
        client.CreateCampaignRequest(budget_amount="100.00", budget_currency="USD")
    )
    svc = service.CampaignService(repo, FakeTargetPolicyBlocking())
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
    allowing = service.CampaignService(repo, FakeTargetPolicyAllowing())
    created = allowing.create_campaign(
        client.CreateCampaignRequest(budget_amount="100.00", budget_currency="USD")
    )
    svc = service.CampaignService(repo, FakeTargetPolicyDown())
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
    svc = service.CampaignService(repo, FakeTargetPolicyAllowing())
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
    svc = service.CampaignService(FakeCampaignStore(), policy)

    with pytest.raises(DomainError) as caught:
        svc.add_link(
            client.AddLinkRequest(
                campaign_id="0123456789abcdef", slug="BAD SLUG", target_url="https://ok.example/x"
            )
        )

    assert caught.value.code == "invalid_slug"
    assert policy.checked == []


def test_add_link_refuses_a_campaign_that_does_not_exist() -> None:
    svc = service.CampaignService(FakeCampaignStore(), FakeTargetPolicyAllowing())

    with pytest.raises(DomainError) as caught:
        svc.add_link(
            client.AddLinkRequest(
                campaign_id="0123456789abcdef", slug="promo", target_url="https://ok.example/x"
            )
        )

    assert caught.value.kind is Kind.NOT_FOUND
    assert caught.value.code == "campaign_missing"


def test_deactivate_link_leaves_the_link_inactive_for_later_readers() -> None:
    svc = service.CampaignService(FakeCampaignStore(), FakeTargetPolicyAllowing())
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
    assert [link.active for link in reread.links] == [False]


def test_deactivate_link_refuses_a_slug_the_campaign_does_not_carry() -> None:
    svc = service.CampaignService(FakeCampaignStore(), FakeTargetPolicyAllowing())
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
    svc = service.CampaignService(FakeCampaignStore(), FakeTargetPolicyAllowing())
    created = svc.create_campaign(
        client.CreateCampaignRequest(budget_amount="99.95", budget_currency="GBP")
    )

    view = svc.get_campaign(client.GetCampaignRequest(campaign_id=created.campaign_id))

    assert view.campaign_id == created.campaign_id
    assert view.budget_amount == "99.95"
    assert view.budget_currency == "GBP"


def test_get_campaign_refuses_a_campaign_that_does_not_exist() -> None:
    svc = service.CampaignService(FakeCampaignStore(), FakeTargetPolicyAllowing())

    with pytest.raises(DomainError) as caught:
        svc.get_campaign(client.GetCampaignRequest(campaign_id="0123456789abcdef"))

    assert caught.value.kind is Kind.NOT_FOUND
    assert caught.value.code == "campaign_missing"


def test_resolve_hands_back_the_target_of_an_active_link() -> None:
    svc = service.CampaignService(FakeCampaignStore(), FakeTargetPolicyAllowing())
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
    svc = service.CampaignService(FakeCampaignStore(), FakeTargetPolicyAllowing())

    with pytest.raises(DomainError) as caught:
        svc.resolve(client.ResolveRequest(slug="nosuch"))

    assert caught.value.kind is Kind.NOT_FOUND
    assert caught.value.code == "link_missing"


def test_resolve_refuses_a_malformed_slug() -> None:
    svc = service.CampaignService(FakeCampaignStore(), FakeTargetPolicyAllowing())

    with pytest.raises(DomainError) as caught:
        svc.resolve(client.ResolveRequest(slug="BAD SLUG"))

    assert caught.value.code == "invalid_slug"


def test_list_links_gathers_the_links_of_every_campaign() -> None:
    svc = service.CampaignService(FakeCampaignStore(), FakeTargetPolicyAllowing())
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
    svc = service.CampaignService(FakeCampaignStore(), FakeTargetPolicyAllowing())
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

    assert [(link.slug, link.active) for link in listed.links] == [("promo", False)]


def test_list_links_is_empty_before_anything_is_created() -> None:
    svc = service.CampaignService(FakeCampaignStore(), FakeTargetPolicyAllowing())

    assert svc.list_links(client.ListLinksRequest()).links == ()
