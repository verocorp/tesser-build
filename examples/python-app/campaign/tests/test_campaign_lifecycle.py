from __future__ import annotations

import json
import pytest

import campaign.adapters.gateways.campaign_identity as campaign_identity
import campaign.adapters.gateways.repo_memory as repo_memory
import campaign.adapters.handlers.http as http
import campaign.application.service as service
import tesser.testing as ts

import campaign.application.ports.target_policy as target_policy
import campaign.client.client as client
import campaign.domain.campaign as campaign
import campaign.domain.money as money
import campaign.domain.short_link as short_link
import campaign.domain.short_links as short_links
import campaign.domain.values as values
from tesser.errors import DomainError, Kind
from protocol.http import HttpRequest
from srv.http.host import respond  # tesser:debt TB070



@ts.fake
class FakeTargetPolicyAllowAll(target_policy.TargetPolicy):
    def check(self, request: target_policy.CheckTargetRequest) -> target_policy.CheckTargetResponse:
        return target_policy.CheckTargetResponse(verdict=target_policy.PolicyVerdict.ALLOWED, reason="ok")


def test_deactivate_link_flips_the_link_inactive() -> None:
    store = repo_memory.InMemoryCampaignRepository()
    svc = service.CampaignService(store, FakeTargetPolicyAllowAll(), campaign_identity.SecretsCampaignIdentity(), store)
    id = svc.create_campaign(client.CreateCampaignRequest(budget_amount="100.00", budget_currency="USD")).campaign_id
    svc.add_link(client.AddLinkRequest(campaign_id=id, slug="promo", target_url="https://ok.example/x"))
    view = svc.deactivate_link(client.DeactivateLinkRequest(campaign_id=id, slug="promo"))
    assert [link.status for link in view.links] == ["inactive"]


def test_deactivate_link_survives_a_reload() -> None:
    store = repo_memory.InMemoryCampaignRepository()
    svc = service.CampaignService(store, FakeTargetPolicyAllowAll(), campaign_identity.SecretsCampaignIdentity(), store)
    id = svc.create_campaign(client.CreateCampaignRequest(budget_amount="100.00", budget_currency="USD")).campaign_id
    svc.add_link(client.AddLinkRequest(campaign_id=id, slug="promo", target_url="https://ok.example/x"))
    svc.deactivate_link(client.DeactivateLinkRequest(campaign_id=id, slug="promo"))
    view = svc.get_campaign(client.GetCampaignRequest(campaign_id=id))
    assert [link.status for link in view.links] == ["inactive"]


def test_resolve_refuses_a_deactivated_link() -> None:
    store = repo_memory.InMemoryCampaignRepository()
    svc = service.CampaignService(store, FakeTargetPolicyAllowAll(), campaign_identity.SecretsCampaignIdentity(), store)
    id = svc.create_campaign(client.CreateCampaignRequest(budget_amount="100.00", budget_currency="USD")).campaign_id
    svc.add_link(client.AddLinkRequest(campaign_id=id, slug="promo", target_url="https://ok.example/x"))
    assert svc.resolve(client.ResolveRequest(slug="promo")).target_url == "https://ok.example/x"
    svc.deactivate_link(client.DeactivateLinkRequest(campaign_id=id, slug="promo"))
    with pytest.raises(DomainError) as e:
        svc.resolve(client.ResolveRequest(slug="promo"))
    assert e.value.kind is Kind.NOT_FOUND
    assert e.value.code == "link_missing"


def test_deactivate_link_rejects_an_unknown_slug() -> None:
    store = repo_memory.InMemoryCampaignRepository()
    svc = service.CampaignService(store, FakeTargetPolicyAllowAll(), campaign_identity.SecretsCampaignIdentity(), store)
    id = svc.create_campaign(client.CreateCampaignRequest(budget_amount="100.00", budget_currency="USD")).campaign_id
    svc.add_link(client.AddLinkRequest(campaign_id=id, slug="promo", target_url="https://ok.example/x"))
    with pytest.raises(DomainError) as e:
        svc.deactivate_link(client.DeactivateLinkRequest(campaign_id=id, slug="nosuch"))
    assert e.value.kind is Kind.NOT_FOUND
    assert e.value.code == "link_missing"


def test_deactivate_link_rejects_an_unknown_campaign() -> None:
    store = repo_memory.InMemoryCampaignRepository()
    svc = service.CampaignService(store, FakeTargetPolicyAllowAll(), campaign_identity.SecretsCampaignIdentity(), store)
    id = svc.create_campaign(client.CreateCampaignRequest(budget_amount="100.00", budget_currency="USD")).campaign_id
    svc.add_link(client.AddLinkRequest(campaign_id=id, slug="promo", target_url="https://ok.example/x"))
    with pytest.raises(DomainError) as e:
        svc.deactivate_link(
            client.DeactivateLinkRequest(campaign_id="fedcba9876543210", slug="promo")
        )
    assert e.value.kind is Kind.NOT_FOUND
    assert e.value.code == "campaign_missing"


def test_deactivate_link_endpoint_returns_the_campaign_payload() -> None:
    store = repo_memory.InMemoryCampaignRepository()
    svc = service.CampaignService(store, FakeTargetPolicyAllowAll(), campaign_identity.SecretsCampaignIdentity(), store)
    id = svc.create_campaign(client.CreateCampaignRequest(budget_amount="100.00", budget_currency="USD")).campaign_id
    svc.add_link(client.AddLinkRequest(campaign_id=id, slug="promo", target_url="https://ok.example/x"))
    handler = http.Handler(svc)
    resp = handler.deactivate_link(
        HttpRequest("POST", "/", {}, {}, {}, json.dumps({"campaign_id": id, "slug": "promo"}).encode("utf-8"))
    )
    assert resp.status_code == 200
    assert resp.json_body()["links"] == [
        {"slug": "promo", "target_url": "https://ok.example/x", "status": "inactive"}
    ]


def test_deactivate_link_endpoint_maps_a_missing_link_to_404() -> None:
    store = repo_memory.InMemoryCampaignRepository()
    svc = service.CampaignService(store, FakeTargetPolicyAllowAll(), campaign_identity.SecretsCampaignIdentity(), store)
    id = svc.create_campaign(client.CreateCampaignRequest(budget_amount="100.00", budget_currency="USD")).campaign_id
    svc.add_link(client.AddLinkRequest(campaign_id=id, slug="promo", target_url="https://ok.example/x"))
    handler = http.Handler(svc)
    resp = respond(
        lambda: handler.deactivate_link(
            HttpRequest("POST", "/", {}, {}, {}, json.dumps({"campaign_id": id, "slug": "nosuch"}).encode("utf-8"))
        )
    )
    assert resp.status_code == 404


def test_resolve_endpoint_maps_a_deactivated_link_to_404() -> None:
    store = repo_memory.InMemoryCampaignRepository()
    svc = service.CampaignService(store, FakeTargetPolicyAllowAll(), campaign_identity.SecretsCampaignIdentity(), store)
    id = svc.create_campaign(client.CreateCampaignRequest(budget_amount="100.00", budget_currency="USD")).campaign_id
    svc.add_link(client.AddLinkRequest(campaign_id=id, slug="promo", target_url="https://ok.example/x"))
    handler = http.Handler(svc)
    svc.deactivate_link(client.DeactivateLinkRequest(campaign_id=id, slug="promo"))
    resp = respond(lambda: handler.resolve(HttpRequest("GET", "/", {"slug": "promo"}, {}, {}, b"")))
    assert resp.status_code == 404


@pytest.mark.parametrize("value", ["", "0123456789ABCDEF", "0123456789abcde", "0123456789abcdefa", "zzz"])
def test_campaign_id_rejects_a_non_hex16_value(value: str) -> None:
    with pytest.raises(DomainError) as e:
        values.CampaignID(value)
    assert e.value.code == "invalid_campaign_id"


@pytest.mark.parametrize("value", ["", "abc", "1.2.3"])
def test_money_amount_rejects_an_unparseable_value(value: str) -> None:
    with pytest.raises(DomainError) as e:
        money.MoneyAmount(value)
    assert e.value.code == "invalid_budget_amount"


def test_money_amount_rejects_a_negative_value() -> None:
    with pytest.raises(DomainError) as e:
        money.MoneyAmount("-0.01")
    assert e.value.code == "invalid_budget_amount"


@pytest.mark.parametrize("value", ["", "us", "usd", "USDD", "US1"])
def test_money_currency_rejects_a_non_iso_code(value: str) -> None:
    with pytest.raises(DomainError) as e:
        money.MoneyCurrency(value)
    assert e.value.code == "invalid_budget_currency"


def test_money_propagates_a_child_rejection() -> None:
    with pytest.raises(DomainError) as e:
        money.Money("1.00", "nope")
    assert e.value.code == "invalid_budget_currency"


def test_campaign_rejects_a_duplicate_slug() -> None:
    with pytest.raises(DomainError) as e:
        campaign.Campaign(
            campaign.CampaignSpec(
                id="0123456789abcdef",
                budget=money.MoneySpec(amount="1.00", currency="USD"),
                links=short_links.ShortLinksSpec(links=(
                    short_link.ShortLinkSpec(slug="promo", target_url="https://ok.example/a", active=True),
                    short_link.ShortLinkSpec(slug="promo", target_url="https://ok.example/b", active=True),
                )),
            )
        )
    assert e.value.kind is Kind.CONFLICT
    assert e.value.code == "duplicate_slug"


def test_campaign_wraps_an_invalid_link_with_its_index() -> None:
    with pytest.raises(DomainError) as e:
        campaign.Campaign(
            campaign.CampaignSpec(
                id="0123456789abcdef",
                budget=money.MoneySpec(amount="1.00", currency="USD"),
                links=short_links.ShortLinksSpec(links=(
                    short_link.ShortLinkSpec(slug="ok", target_url="https://ok.example/a", active=True),
                    short_link.ShortLinkSpec(slug="BAD SLUG", target_url="https://ok.example/b", active=True),
                )),
            )
        )
    assert e.value.code == "invalid_short_link"
    assert "index 1" in e.value.message


def test_create_campaign_endpoint_rejects_a_non_object_budget() -> None:
    store = repo_memory.InMemoryCampaignRepository()
    handler = http.Handler(service.CampaignService(store, FakeTargetPolicyAllowAll(), campaign_identity.SecretsCampaignIdentity(), store))
    resp = respond(
        lambda: handler.create_campaign(
            HttpRequest("POST", "/", {}, {}, {}, json.dumps({"budget": "100.00"}).encode("utf-8"))
        )
    )
    assert resp.status_code == 400
    assert resp.json_body()["type"] == "/problems/malformed_request"
