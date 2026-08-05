from __future__ import annotations

import dataclasses
import json
import pathlib

import campaign.client
import linkpolicy.client
import reports.client
from campaign.adapters.handlers.http import Handler
from campaign.client import LinkView, ResolveResponse
from campaign.wiring.config import Config as CampaignConfig
from campaign.wiring.wire import build as build_campaign
from errors import InfraError
from httpwire import HttpRequest, decode_body
from reports.adapters.handlers.http import Handler as ReportsHandler
from reports.client import LinkVerdictView
from tests.discovery import discovered_contexts

ROOT = pathlib.Path(__file__).resolve().parent.parent


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
    assert dataclasses.is_dataclass(ResolveResponse)
    for field in dataclasses.fields(ResolveResponse):
        assert field.type in ("str", str), field
    assert dataclasses.is_dataclass(LinkView)
    for field in dataclasses.fields(LinkView):
        assert field.type in ("str", str, "bool", bool), field
    assert dataclasses.is_dataclass(LinkVerdictView)
    for field in dataclasses.fields(LinkVerdictView):
        assert field.type in ("str", str, "bool", bool), field


def test_config_lives_in_wiring_not_on_public_top_level() -> None:
    for ctx in discovered_contexts():
        assert (ROOT / ctx / "wiring" / "config.py").is_file()
        assert not (ROOT / ctx / "config.py").exists(), f"{ctx} config leaked to the public top level"


class _AllowAllChecker:
    def check(self, target_url: str) -> campaign.client.CheckOutcome:
        return campaign.client.CheckOutcome(True, "ok")


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
    created_body = decode_body(created.body)
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
    assert decode_body(added.body) == {
        "campaign_id": campaign_id,
        "budget": {"amount": "100.00", "currency": "USD"},
        "links": [{"slug": "promo", "target_url": "https://ok.example/x", "active": True}],
    }


class _StubReports:
    def links_by_verdict(self) -> tuple[LinkVerdictView, ...]:
        return (LinkVerdictView("promo", "https://ok.example/x", False, "host blocked"),)


class _FailingReports:
    def links_by_verdict(self) -> tuple[LinkVerdictView, ...]:
        raise InfraError("the campaign store is unreachable")


def test_reports_handler_translates_client_dtos_to_wire() -> None:
    resp = ReportsHandler(_StubReports()).links_by_verdict(HttpRequest())
    assert resp.status_code == 200
    assert decode_body(resp.body) == {
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
    assert decode_body(resp.body) == {
        "type": "/problems/unavailable",
        "detail": "a dependency is unavailable; please retry",
    }
