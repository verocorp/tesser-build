"""Shape properties: the four roles are present per context; the public seam is
Client + primitive DTOs at the top level; each context's config lives in its
``wiring`` (impl), not on the public top level; the handler translates wire<->Client
DTOs.
"""

from __future__ import annotations

import dataclasses
import pathlib

import campaign
import linkpolicy
from campaign.adapters.handlers.http import Handler
from campaign.client import CreateLinkResponse
from campaign.wiring.config import Config as CampaignConfig
from campaign.wiring.wire import build as build_campaign

ROOT = pathlib.Path(__file__).resolve().parent.parent


def test_four_roles_present_per_context() -> None:
    for ctx in ("campaign", "linkpolicy"):
        for role in ("domain", "application", "adapters", "wiring"):
            assert (ROOT / ctx / role).is_dir(), f"{ctx}/{role} missing"


def test_public_seam_is_client_plus_dtos_at_top_level() -> None:
    assert hasattr(campaign, "Client")
    assert hasattr(linkpolicy, "Client")
    # Client DTOs are frozen dataclasses with primitive leaves.
    assert dataclasses.is_dataclass(CreateLinkResponse)
    for field in dataclasses.fields(CreateLinkResponse):
        assert field.type in ("str", str), field


def test_config_lives_in_wiring_not_on_public_top_level() -> None:
    for ctx in ("campaign", "linkpolicy"):
        assert (ROOT / ctx / "wiring" / "config.py").is_file()
        assert not (ROOT / ctx / "config.py").exists(), f"{ctx} config leaked to the public top level"


class _AllowAllChecker:
    def check(self, target_url: str) -> campaign.CheckOutcome:
        return campaign.CheckOutcome(True, "ok")


def test_handler_translates_wire_to_client_dtos() -> None:
    client, _ = build_campaign(CampaignConfig("memory"), _AllowAllChecker())
    handler = Handler(client)
    resp = handler.create_link('{"slug": "promo", "target_url": "https://ok.example/x"}')
    assert resp.status == 201
    assert resp.body == {"slug": "promo", "target_url": "https://ok.example/x"}
