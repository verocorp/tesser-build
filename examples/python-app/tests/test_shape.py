from __future__ import annotations

import inspect
import json

import campaign.client.client as campaign_client
import linkpolicy.client.client as linkpolicy_client
import reports.client.client as reports_client
import tesser.context  # tesser:debt TB050
import tesser.testing as ts
import campaign.adapters.handlers.http as http  # tesser:debt TB070
import campaign.client.client as client
from tesser.errors import InfraError
from protocol.http import HttpRequest
import reports.adapters.handlers.http as reports_http  # tesser:debt TB070
import reports.client.client as reports_client2
from srv.http.host import respond
from tests.discovery import discovered_contexts

from tests.support import ROOT




def test_required_roles_present_per_context() -> None:
    for ctx in discovered_contexts():
        for role in ("domain", "application", "component"):
            assert (ROOT / ctx / role).is_dir(), f"{ctx}/{role} missing"


def test_public_interface_is_client_plus_dtos_in_the_client_module() -> None:
    assert hasattr(campaign_client, "Client")
    assert hasattr(linkpolicy_client, "Client")
    assert hasattr(reports_client, "Client")
    for ctx in discovered_contexts():
        init_source = (ROOT / ctx / "__init__.py").read_text()
        assert init_source == "", f"{ctx}/__init__.py must be empty; the interface lives in the client role"
    for dto in (client.ResolveResponse, client.LinkView, reports_client2.LinkVerdictView):
        assert tesser.context.Response in dto.__mro__, f"{dto.__name__} must declare ts.Response"
        params = inspect.signature(dto.__init__).parameters
        for name, param in params.items():
            if name == "self":
                continue
            assert param.annotation in ("str", "bool", "tuple[LinkView, ...]"), (
                f"{dto.__name__}.{name} is not a primitive DTO field: {param.annotation}"
            )


def test_config_lives_in_the_component_not_on_the_public_top_level() -> None:
    for ctx in discovered_contexts():
        assert (ROOT / ctx / "component" / "config.py").is_file()
        assert not (ROOT / ctx / "config.py").exists(), f"{ctx} config leaked to the public top level"


@ts.fake
class FakeCampaignClientScripted(campaign_client.Client):
    def __init__(self, *views: campaign_client.CampaignView) -> None:
        self.pending = list(views)
        self.requests: list[object] = []

    def _next(self, request: object) -> campaign_client.CampaignView:  # tesser:debt TB051
        self.requests.append(request)
        return self.pending.pop(0)

    def create_campaign(
        self, req: campaign_client.CreateCampaignRequest
    ) -> campaign_client.CampaignView:
        return self._next(req)

    def add_link(self, req: campaign_client.AddLinkRequest) -> campaign_client.CampaignView:
        return self._next(req)

    def deactivate_link(
        self, req: campaign_client.DeactivateLinkRequest
    ) -> campaign_client.CampaignView:
        return self._next(req)

    def get_campaign(
        self, req: campaign_client.GetCampaignRequest
    ) -> campaign_client.CampaignView:
        return self._next(req)

    def resolve(self, req: campaign_client.ResolveRequest) -> client.ResolveResponse:
        raise AssertionError("resolve is not under test here")

    def list_links(
        self, req: campaign_client.ListLinksRequest
    ) -> campaign_client.ListLinksResponse:
        raise AssertionError("list_links is not under test here")


def test_handler_translates_wire_to_client_dtos() -> None:
    scripted = FakeCampaignClientScripted(
        campaign_client.CampaignView("0123456789abcdef", "100.00", "USD", ()),
        campaign_client.CampaignView(
            "0123456789abcdef",
            "100.00",
            "USD",
            (client.LinkView("promo", "https://ok.example/x", "active"),),
        ),
    )
    handler = http.Handler(scripted)
    created = handler.create_campaign(
        HttpRequest(
            "POST", "/", {}, {}, {},
            json.dumps({"budget": {"amount": "100.00", "currency": "USD"}}).encode("utf-8"),
        )
    )
    assert created.status_code == 201
    assert created.json_body() == {
        "campaign_id": "0123456789abcdef",
        "budget": {"amount": "100.00", "currency": "USD"},
        "links": [],
    }
    create_request = scripted.requests[0]
    assert isinstance(create_request, campaign_client.CreateCampaignRequest)
    assert create_request.budget_amount == "100.00"
    assert create_request.budget_currency == "USD"
    added = handler.add_link(
        HttpRequest(
            "POST", "/", {}, {}, {},
            json.dumps(
                {
                    "campaign_id": "0123456789abcdef",
                    "slug": "promo",
                    "target_url": "https://ok.example/x",
                }
            ).encode("utf-8"),
        )
    )
    assert added.status_code == 200
    assert added.json_body() == {
        "campaign_id": "0123456789abcdef",
        "budget": {"amount": "100.00", "currency": "USD"},
        "links": [{"slug": "promo", "target_url": "https://ok.example/x", "status": "active"}],
    }
    add_request = scripted.requests[1]
    assert isinstance(add_request, campaign_client.AddLinkRequest)
    assert add_request.campaign_id == "0123456789abcdef"
    assert add_request.slug == "promo"


@ts.fake
class FakeReportsClientStub(reports_client.Client):
    def links_by_verdict(self, req: reports_client2.LinksByVerdictRequest) -> reports_client2.LinksByVerdictResponse:
        return reports_client2.LinksByVerdictResponse(
            links=(reports_client2.LinkVerdictView("promo", "https://ok.example/x", False, "host blocked"),)
        )


@ts.fake
class FakeReportsClientFailing(reports_client.Client):
    def links_by_verdict(self, req: reports_client2.LinksByVerdictRequest) -> reports_client2.LinksByVerdictResponse:
        raise InfraError("the campaign store is unreachable")


def test_reports_handler_translates_client_dtos_to_component() -> None:
    resp = reports_http.Handler(FakeReportsClientStub()).links_by_verdict(HttpRequest("GET", "/", {}, {}, {}, b""))
    assert resp.status_code == 200
    assert resp.json_body() == {
        "links": [
            {
                "slug": "promo",
                "target_url": "https://ok.example/x",
                "allowed": False,
                "reason": "host blocked",
            }
        ]
    }


def test_reports_handler_maps_a_failure_to_a_problem_document() -> None:
    resp = respond(lambda: reports_http.Handler(FakeReportsClientFailing()).links_by_verdict(HttpRequest("GET", "/", {}, {}, {}, b"")))
    assert resp.status_code == 503
    assert resp.json_body() == {
        "type": "/problems/unavailable",
        "detail": "a dependency is unavailable; please retry",
    }
