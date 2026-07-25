from __future__ import annotations

import pytest

from campaign.adapters.gateways.repo_memory import InMemoryCampaignRepository
from campaign.adapters.handlers.http import Handler
from campaign.application.service import CampaignService
from campaign.client import (
    AddLinkRequest,
    CheckOutcome,
    CreateCampaignRequest,
    DeactivateLinkRequest,
    GetCampaignRequest,
    ResolveRequest,
)
from campaign.domain.campaign import Campaign, CampaignSpec
from campaign.domain.money import Money, MoneyAmount, MoneyCurrency, MoneySpec
from campaign.domain.short_link import ShortLinkSpec
from campaign.domain.values import CampaignID
from errors import DomainError, Kind
from httpwire import HttpRequest

_CAMPAIGN_ID = "0123456789abcdef"


class _AllowAll:
    def check(self, target_url: str) -> CheckOutcome:
        return CheckOutcome(True, "ok")


def _service() -> CampaignService:
    return CampaignService(InMemoryCampaignRepository(), _AllowAll())


def _campaign_with_link(svc: CampaignService) -> str:
    view = svc.create_campaign(CreateCampaignRequest(budget_amount="100.00", budget_currency="USD"))
    svc.add_link(
        AddLinkRequest(
            campaign_id=view.campaign_id, slug="promo", target_url="https://ok.example/x"
        )
    )
    return view.campaign_id


def test_deactivate_link_flips_the_link_inactive() -> None:
    svc = _service()
    id = _campaign_with_link(svc)
    view = svc.deactivate_link(DeactivateLinkRequest(campaign_id=id, slug="promo"))
    assert [link.active for link in view.links] == [False]


def test_deactivate_link_survives_a_reload() -> None:
    svc = _service()
    id = _campaign_with_link(svc)
    svc.deactivate_link(DeactivateLinkRequest(campaign_id=id, slug="promo"))
    view = svc.get_campaign(GetCampaignRequest(campaign_id=id))
    assert [link.active for link in view.links] == [False]


def test_resolve_refuses_a_deactivated_link() -> None:
    svc = _service()
    id = _campaign_with_link(svc)
    assert svc.resolve(ResolveRequest(slug="promo")).target_url == "https://ok.example/x"
    svc.deactivate_link(DeactivateLinkRequest(campaign_id=id, slug="promo"))
    with pytest.raises(DomainError) as e:
        svc.resolve(ResolveRequest(slug="promo"))
    assert e.value.kind is Kind.NOT_FOUND
    assert e.value.code == "link_missing"


def test_deactivate_link_rejects_an_unknown_slug() -> None:
    svc = _service()
    id = _campaign_with_link(svc)
    with pytest.raises(DomainError) as e:
        svc.deactivate_link(DeactivateLinkRequest(campaign_id=id, slug="nosuch"))
    assert e.value.kind is Kind.NOT_FOUND
    assert e.value.code == "link_missing"


def test_deactivate_link_rejects_an_unknown_campaign() -> None:
    svc = _service()
    _campaign_with_link(svc)
    with pytest.raises(DomainError) as e:
        svc.deactivate_link(
            DeactivateLinkRequest(campaign_id="fedcba9876543210", slug="promo")
        )
    assert e.value.kind is Kind.NOT_FOUND
    assert e.value.code == "campaign_missing"


def test_deactivate_link_endpoint_returns_the_campaign_payload() -> None:
    svc = _service()
    id = _campaign_with_link(svc)
    handler = Handler(svc)
    resp = handler.deactivate_link(HttpRequest(body={"campaign_id": id, "slug": "promo"}))
    assert resp.status_code == 200
    assert resp.body["links"] == [
        {"slug": "promo", "target_url": "https://ok.example/x", "active": False}
    ]


def test_deactivate_link_endpoint_maps_a_missing_link_to_404() -> None:
    svc = _service()
    id = _campaign_with_link(svc)
    handler = Handler(svc)
    resp = handler.deactivate_link(HttpRequest(body={"campaign_id": id, "slug": "nosuch"}))
    assert resp.status_code == 404


def test_resolve_endpoint_maps_a_deactivated_link_to_404() -> None:
    svc = _service()
    id = _campaign_with_link(svc)
    handler = Handler(svc)
    svc.deactivate_link(DeactivateLinkRequest(campaign_id=id, slug="promo"))
    assert handler.resolve(HttpRequest(path_params={"slug": "promo"})).status_code == 404


@pytest.mark.parametrize("value", ["", "0123456789ABCDEF", "0123456789abcde", "0123456789abcdefa", "zzz"])
def test_campaign_id_rejects_a_non_hex16_value(value: str) -> None:
    with pytest.raises(DomainError) as e:
        CampaignID(value)
    assert e.value.code == "invalid_campaign_id"


@pytest.mark.parametrize("value", ["", "abc", "1.2.3"])
def test_money_amount_rejects_an_unparseable_value(value: str) -> None:
    with pytest.raises(DomainError) as e:
        MoneyAmount(value)
    assert e.value.code == "invalid_budget_amount"


def test_money_amount_rejects_a_negative_value() -> None:
    with pytest.raises(DomainError) as e:
        MoneyAmount("-0.01")
    assert e.value.code == "invalid_budget_amount"


@pytest.mark.parametrize("value", ["", "us", "usd", "USDD", "US1"])
def test_money_currency_rejects_a_non_iso_code(value: str) -> None:
    with pytest.raises(DomainError) as e:
        MoneyCurrency(value)
    assert e.value.code == "invalid_budget_currency"


def test_money_propagates_a_child_rejection() -> None:
    with pytest.raises(DomainError) as e:
        Money(MoneySpec(amount="1.00", currency="nope"))
    assert e.value.code == "invalid_budget_currency"


def test_campaign_rejects_a_duplicate_slug() -> None:
    with pytest.raises(DomainError) as e:
        Campaign(
            CampaignSpec(
                id=_CAMPAIGN_ID,
                budget=MoneySpec(amount="1.00", currency="USD"),
                links=(
                    ShortLinkSpec(slug="promo", target_url="https://ok.example/a", active=True),
                    ShortLinkSpec(slug="promo", target_url="https://ok.example/b", active=True),
                ),
            )
        )
    assert e.value.kind is Kind.CONFLICT
    assert e.value.code == "duplicate_slug"


def test_campaign_wraps_an_invalid_link_with_its_index() -> None:
    with pytest.raises(DomainError) as e:
        Campaign(
            CampaignSpec(
                id=_CAMPAIGN_ID,
                budget=MoneySpec(amount="1.00", currency="USD"),
                links=(
                    ShortLinkSpec(slug="ok", target_url="https://ok.example/a", active=True),
                    ShortLinkSpec(slug="BAD SLUG", target_url="https://ok.example/b", active=True),
                ),
            )
        )
    assert e.value.code == "invalid_short_link"
    assert "index 1" in e.value.message


def test_create_campaign_endpoint_rejects_a_non_object_budget() -> None:
    handler = Handler(_service())
    resp = handler.create_campaign(HttpRequest(body={"budget": "100.00"}))
    assert resp.status_code == 400
    assert resp.body["type"] == "/problems/malformed_request"
