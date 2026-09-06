from __future__ import annotations

import json
import pytest

import tesser.testing as ts

import campaign.adapters.gateways as gateways
import campaign.adapters.handlers as handlers
import campaign.adapters.repositories as repositories
import campaign.application as application
import campaign.application.ports as ports
import campaign.client as client
import campaign.domain as domain
import protocol as protocol
import tesser.errors as errors


@ts.fake
class FakeTargetPolicyAllowAll(ports.TargetPolicy):
    def check(self, check_target_request: ports.CheckTargetRequest) -> ports.CheckTargetResponse:
        return ports.CheckTargetResponse(verdict=ports.PolicyVerdict.ALLOWED, reason="ok")


def test_deactivate_link_flips_the_link_inactive() -> None:
    in_memory_campaign_repository = repositories.InMemoryCampaignRepository()
    campaign_service = application.CampaignService(in_memory_campaign_repository, FakeTargetPolicyAllowAll(), gateways.SecretsCampaignIdentity(), in_memory_campaign_repository)
    id = campaign_service.create_campaign(client.CreateCampaignRequest(budget_amount="100.00", budget_currency="USD")).campaign_id
    campaign_service.add_link(client.AddLinkRequest(campaign_id=id, slug="promo", target_url="https://ok.example/x"))
    campaign_view = campaign_service.deactivate_link(client.DeactivateLinkRequest(campaign_id=id, slug="promo"))
    assert [link.status for link in campaign_view.links] == ["inactive"]


def test_deactivate_link_survives_a_reload() -> None:
    in_memory_campaign_repository = repositories.InMemoryCampaignRepository()
    campaign_service = application.CampaignService(in_memory_campaign_repository, FakeTargetPolicyAllowAll(), gateways.SecretsCampaignIdentity(), in_memory_campaign_repository)
    id = campaign_service.create_campaign(client.CreateCampaignRequest(budget_amount="100.00", budget_currency="USD")).campaign_id
    campaign_service.add_link(client.AddLinkRequest(campaign_id=id, slug="promo", target_url="https://ok.example/x"))
    campaign_service.deactivate_link(client.DeactivateLinkRequest(campaign_id=id, slug="promo"))
    campaign_view = campaign_service.get_campaign(client.GetCampaignRequest(campaign_id=id))
    assert [link.status for link in campaign_view.links] == ["inactive"]


def test_resolve_refuses_a_deactivated_link() -> None:
    in_memory_campaign_repository = repositories.InMemoryCampaignRepository()
    campaign_service = application.CampaignService(in_memory_campaign_repository, FakeTargetPolicyAllowAll(), gateways.SecretsCampaignIdentity(), in_memory_campaign_repository)
    id = campaign_service.create_campaign(client.CreateCampaignRequest(budget_amount="100.00", budget_currency="USD")).campaign_id
    campaign_service.add_link(client.AddLinkRequest(campaign_id=id, slug="promo", target_url="https://ok.example/x"))
    assert campaign_service.resolve(client.ResolveRequest(slug="promo")).target_url == "https://ok.example/x"
    campaign_service.deactivate_link(client.DeactivateLinkRequest(campaign_id=id, slug="promo"))
    with pytest.raises(errors.DomainError) as e:
        campaign_service.resolve(client.ResolveRequest(slug="promo"))
    assert e.value.kind is errors.Kind.NOT_FOUND
    assert e.value.code == "link_missing"


def test_deactivate_link_rejects_an_unknown_slug() -> None:
    in_memory_campaign_repository = repositories.InMemoryCampaignRepository()
    campaign_service = application.CampaignService(in_memory_campaign_repository, FakeTargetPolicyAllowAll(), gateways.SecretsCampaignIdentity(), in_memory_campaign_repository)
    id = campaign_service.create_campaign(client.CreateCampaignRequest(budget_amount="100.00", budget_currency="USD")).campaign_id
    campaign_service.add_link(client.AddLinkRequest(campaign_id=id, slug="promo", target_url="https://ok.example/x"))
    with pytest.raises(errors.DomainError) as e:
        campaign_service.deactivate_link(client.DeactivateLinkRequest(campaign_id=id, slug="nosuch"))
    assert e.value.kind is errors.Kind.NOT_FOUND
    assert e.value.code == "link_missing"


def test_deactivate_link_rejects_an_unknown_campaign() -> None:
    in_memory_campaign_repository = repositories.InMemoryCampaignRepository()
    campaign_service = application.CampaignService(in_memory_campaign_repository, FakeTargetPolicyAllowAll(), gateways.SecretsCampaignIdentity(), in_memory_campaign_repository)
    id = campaign_service.create_campaign(client.CreateCampaignRequest(budget_amount="100.00", budget_currency="USD")).campaign_id
    campaign_service.add_link(client.AddLinkRequest(campaign_id=id, slug="promo", target_url="https://ok.example/x"))
    with pytest.raises(errors.DomainError) as e:
        campaign_service.deactivate_link(
            client.DeactivateLinkRequest(campaign_id="fedcba9876543210", slug="promo")
        )
    assert e.value.kind is errors.Kind.NOT_FOUND
    assert e.value.code == "campaign_missing"


def test_deactivate_link_endpoint_returns_the_campaign_payload() -> None:
    in_memory_campaign_repository = repositories.InMemoryCampaignRepository()
    campaign_service = application.CampaignService(in_memory_campaign_repository, FakeTargetPolicyAllowAll(), gateways.SecretsCampaignIdentity(), in_memory_campaign_repository)
    id = campaign_service.create_campaign(client.CreateCampaignRequest(budget_amount="100.00", budget_currency="USD")).campaign_id
    campaign_service.add_link(client.AddLinkRequest(campaign_id=id, slug="promo", target_url="https://ok.example/x"))
    http_handler = handlers.HttpHandler(campaign_service)
    http_response = http_handler.deactivate_link(
        protocol.HttpRequest("POST", "/", {}, {}, {}, json.dumps({"campaign_id": id, "slug": "promo"}).encode("utf-8"))
    )
    assert http_response.status_code == 200
    assert http_response.json_body()["links"] == [
        {"slug": "promo", "target_url": "https://ok.example/x", "status": "inactive"}
    ]


def test_deactivate_link_endpoint_maps_a_missing_link_to_404() -> None:
    in_memory_campaign_repository = repositories.InMemoryCampaignRepository()
    campaign_service = application.CampaignService(in_memory_campaign_repository, FakeTargetPolicyAllowAll(), gateways.SecretsCampaignIdentity(), in_memory_campaign_repository)
    id = campaign_service.create_campaign(client.CreateCampaignRequest(budget_amount="100.00", budget_currency="USD")).campaign_id
    campaign_service.add_link(client.AddLinkRequest(campaign_id=id, slug="promo", target_url="https://ok.example/x"))
    http_handler = handlers.HttpHandler(campaign_service)
    try:
        http_response = http_handler.deactivate_link(
            protocol.HttpRequest("POST", "/", {}, {}, {}, json.dumps({"campaign_id": id, "slug": "nosuch"}).encode("utf-8"))
        )
    except protocol.BadRequest as e:
        http_response = protocol.HttpResponse.problem(400, "malformed_request", str(e))
    except protocol.PayloadTooLarge as e:
        http_response = protocol.HttpResponse.problem(413, "payload_too_large", str(e))
    except protocol.StreamingUnsupported as e:
        http_response = protocol.HttpResponse.problem(411, "length_required", str(e))
    except errors.DomainError as e:
        http_response = protocol.HttpResponse.problem(errors.status_for(e.kind), e.code, e.message)
    except errors.InfraError:
        http_response = protocol.HttpResponse.problem(503, "unavailable", "a dependency is unavailable; please retry")
    except Exception:
        http_response = protocol.HttpResponse.problem(500, "internal", "unexpected error")
    assert http_response.status_code == 404


def test_resolve_endpoint_maps_a_deactivated_link_to_404() -> None:
    in_memory_campaign_repository = repositories.InMemoryCampaignRepository()
    campaign_service = application.CampaignService(in_memory_campaign_repository, FakeTargetPolicyAllowAll(), gateways.SecretsCampaignIdentity(), in_memory_campaign_repository)
    id = campaign_service.create_campaign(client.CreateCampaignRequest(budget_amount="100.00", budget_currency="USD")).campaign_id
    campaign_service.add_link(client.AddLinkRequest(campaign_id=id, slug="promo", target_url="https://ok.example/x"))
    http_handler = handlers.HttpHandler(campaign_service)
    campaign_service.deactivate_link(client.DeactivateLinkRequest(campaign_id=id, slug="promo"))
    try:
        http_response = http_handler.resolve(protocol.HttpRequest("GET", "/", {"slug": "promo"}, {}, {}, b""))
    except protocol.BadRequest as e:
        http_response = protocol.HttpResponse.problem(400, "malformed_request", str(e))
    except protocol.PayloadTooLarge as e:
        http_response = protocol.HttpResponse.problem(413, "payload_too_large", str(e))
    except protocol.StreamingUnsupported as e:
        http_response = protocol.HttpResponse.problem(411, "length_required", str(e))
    except errors.DomainError as e:
        http_response = protocol.HttpResponse.problem(errors.status_for(e.kind), e.code, e.message)
    except errors.InfraError:
        http_response = protocol.HttpResponse.problem(503, "unavailable", "a dependency is unavailable; please retry")
    except Exception:
        http_response = protocol.HttpResponse.problem(500, "internal", "unexpected error")
    assert http_response.status_code == 404


@pytest.mark.parametrize("value", ["", "0123456789ABCDEF", "0123456789abcde", "0123456789abcdefa", "zzz"])
def test_campaign_id_rejects_a_non_hex16_value(value: str) -> None:
    with pytest.raises(errors.DomainError) as e:
        domain.CampaignID(value)
    assert e.value.code == "invalid_campaign_id"


@pytest.mark.parametrize("value", ["", "abc", "1.2.3"])
def test_money_amount_rejects_an_unparseable_value(value: str) -> None:
    with pytest.raises(errors.DomainError) as e:
        domain.MoneyAmount(value)
    assert e.value.code == "invalid_budget_amount"


def test_money_amount_rejects_a_negative_value() -> None:
    with pytest.raises(errors.DomainError) as e:
        domain.MoneyAmount("-0.01")
    assert e.value.code == "invalid_budget_amount"


@pytest.mark.parametrize("value", ["", "us", "usd", "USDD", "US1"])
def test_money_currency_rejects_a_non_iso_code(value: str) -> None:
    with pytest.raises(errors.DomainError) as e:
        domain.MoneyCurrency(value)
    assert e.value.code == "invalid_budget_currency"


def test_money_propagates_a_child_rejection() -> None:
    with pytest.raises(errors.DomainError) as e:
        domain.Money(domain.MoneySpec("1.00", "nope"))
    assert e.value.code == "invalid_budget_currency"


def test_campaign_rejects_a_duplicate_slug() -> None:
    with pytest.raises(errors.DomainError) as e:
        domain.Campaign(
            domain.CampaignSpec(
                id="0123456789abcdef",
                budget=domain.MoneySpec(amount="1.00", currency="USD"),
                links=domain.ShortLinksSpec(links=(
                    domain.ShortLinkSpec(slug="promo", target_url="https://ok.example/a", active=True),
                    domain.ShortLinkSpec(slug="promo", target_url="https://ok.example/b", active=True),
                )),
            )
        )
    assert e.value.kind is errors.Kind.CONFLICT
    assert e.value.code == "duplicate_slug"


def test_campaign_wraps_an_invalid_link_with_its_index() -> None:
    with pytest.raises(errors.DomainError) as e:
        domain.Campaign(
            domain.CampaignSpec(
                id="0123456789abcdef",
                budget=domain.MoneySpec(amount="1.00", currency="USD"),
                links=domain.ShortLinksSpec(links=(
                    domain.ShortLinkSpec(slug="ok", target_url="https://ok.example/a", active=True),
                    domain.ShortLinkSpec(slug="BAD SLUG", target_url="https://ok.example/b", active=True),
                )),
            )
        )
    assert e.value.code == "invalid_short_link"
    assert "index 1" in e.value.message


def test_create_campaign_endpoint_rejects_a_non_object_budget() -> None:
    in_memory_campaign_repository = repositories.InMemoryCampaignRepository()
    http_handler = handlers.HttpHandler(application.CampaignService(in_memory_campaign_repository, FakeTargetPolicyAllowAll(), gateways.SecretsCampaignIdentity(), in_memory_campaign_repository))
    try:
        http_response = http_handler.create_campaign(
            protocol.HttpRequest("POST", "/", {}, {}, {}, json.dumps({"budget": "100.00"}).encode("utf-8"))
        )
    except protocol.BadRequest as e:
        http_response = protocol.HttpResponse.problem(400, "malformed_request", str(e))
    except protocol.PayloadTooLarge as e:
        http_response = protocol.HttpResponse.problem(413, "payload_too_large", str(e))
    except protocol.StreamingUnsupported as e:
        http_response = protocol.HttpResponse.problem(411, "length_required", str(e))
    except errors.DomainError as e:
        http_response = protocol.HttpResponse.problem(errors.status_for(e.kind), e.code, e.message)
    except errors.InfraError:
        http_response = protocol.HttpResponse.problem(503, "unavailable", "a dependency is unavailable; please retry")
    except Exception:
        http_response = protocol.HttpResponse.problem(500, "internal", "unexpected error")
    assert http_response.status_code == 400
    assert http_response.json_body()["type"] == "/problems/malformed_request"


def test_add_link_keeps_an_earlier_deactivated_link_inactive() -> None:
    in_memory_campaign_repository = repositories.InMemoryCampaignRepository()
    campaign_service = application.CampaignService(in_memory_campaign_repository, FakeTargetPolicyAllowAll(), gateways.SecretsCampaignIdentity(), in_memory_campaign_repository)
    id = campaign_service.create_campaign(client.CreateCampaignRequest(budget_amount="100.00", budget_currency="USD")).campaign_id
    campaign_service.add_link(client.AddLinkRequest(campaign_id=id, slug="promo", target_url="https://ok.example/x"))
    campaign_service.deactivate_link(client.DeactivateLinkRequest(campaign_id=id, slug="promo"))
    campaign_view = campaign_service.add_link(client.AddLinkRequest(campaign_id=id, slug="sale", target_url="https://ok.example/y"))
    assert [(link.slug, link.status) for link in campaign_view.links] == [
        ("promo", "inactive"),
        ("sale", "active"),
    ]
