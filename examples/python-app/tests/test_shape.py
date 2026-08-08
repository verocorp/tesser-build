from __future__ import annotations

import inspect
import json

import campaign.client
import linkpolicy.client
import reports.client
import tesser.context
import tesser.testing as ts
from campaign.adapters.handlers.http import Handler
from campaign.application.parts import CheckOutcome
from campaign.application.service import TargetChecker
from campaign.client import LinkView, ResolveResponse
from campaign.wiring.config import Config as CampaignConfig
from campaign.wiring.wire import build as build_campaign
from errors import InfraError
from httpwire import HttpRequest
from reports.adapters.handlers.http import Handler as ReportsHandler
from reports.client import LinksByVerdictRequest, LinksByVerdictResponse, LinkVerdictView
from tests.discovery import discovered_contexts

from tests.support import ROOT


def test_required_roles_present_per_context() -> None:
    for ctx in discovered_contexts():
        for role in ("domain", "application", "wiring"):
            assert (ROOT / ctx / role).is_dir(), f"{ctx}/{role} missing"


def test_public_interface_is_client_plus_dtos_in_the_client_module() -> None:
    assert hasattr(campaign.client, "Client")
    assert hasattr(linkpolicy.client, "Client")
    assert hasattr(reports.client, "Client")
    for ctx in discovered_contexts():
        init_source = (ROOT / ctx / "__init__.py").read_text()
        assert init_source == "", f"{ctx}/__init__.py must be empty; the interface lives in client.py"
    for dto in (ResolveResponse, LinkView, LinkVerdictView):
        assert tesser.context.Response in dto.__mro__, f"{dto.__name__} must declare ts.Response"
        params = inspect.signature(dto.__init__).parameters
        for name, param in params.items():
            if name == "self":
                continue
            assert param.annotation in ("str", "bool", "tuple[LinkView, ...]"), (
                f"{dto.__name__}.{name} is not a primitive DTO field: {param.annotation}"
            )


def test_config_lives_in_wiring_not_on_public_top_level() -> None:
    for ctx in discovered_contexts():
        assert (ROOT / ctx / "wiring" / "config.py").is_file()
        assert not (ROOT / ctx / "config.py").exists(), f"{ctx} config leaked to the public top level"


@ts.fake
class _AllowAllChecker(TargetChecker):
    def check(self, target_url: str) -> CheckOutcome:
        return CheckOutcome(True, "ok")


def test_handler_translates_wire_to_client_dtos() -> None:
    client, _ = build_campaign(CampaignConfig("memory"), _AllowAllChecker())
    handler = Handler(client)
    created = handler.create_campaign(
        HttpRequest(
            body=json.dumps(
                {"budget": {"amount": "100.00", "currency": "USD"}}
            ).encode("utf-8")
        )
    )
    assert created.status_code == 201
    created_body = created.json_body()
    campaign_id = created_body["campaign_id"]
    assert created_body == {
        "campaign_id": campaign_id,
        "budget": {"amount": "100.00", "currency": "USD"},
        "links": [],
    }
    added = handler.add_link(
        HttpRequest(
            body=json.dumps(
                {"campaign_id": campaign_id, "slug": "promo", "target_url": "https://ok.example/x"}
            ).encode("utf-8")
        )
    )
    assert added.status_code == 200
    assert added.json_body() == {
        "campaign_id": campaign_id,
        "budget": {"amount": "100.00", "currency": "USD"},
        "links": [{"slug": "promo", "target_url": "https://ok.example/x", "active": True}],
    }


@ts.fake
class _StubReports(reports.client.Client):
    def links_by_verdict(self, req: LinksByVerdictRequest) -> LinksByVerdictResponse:
        return LinksByVerdictResponse(
            links=(LinkVerdictView("promo", "https://ok.example/x", False, "host blocked"),)
        )


@ts.fake
class _FailingReports(reports.client.Client):
    def links_by_verdict(self, req: LinksByVerdictRequest) -> LinksByVerdictResponse:
        raise InfraError("the campaign store is unreachable")


def test_reports_handler_translates_client_dtos_to_wire() -> None:
    resp = ReportsHandler(_StubReports()).links_by_verdict(HttpRequest())
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
    resp = ReportsHandler(_FailingReports()).links_by_verdict(HttpRequest())
    assert resp.status_code == 503
    assert resp.json_body() == {
        "type": "/problems/unavailable",
        "detail": "a dependency is unavailable; please retry",
    }
