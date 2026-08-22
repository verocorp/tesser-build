from __future__ import annotations

import typing

import tesser.application as ts

import campaign.application.ports.campaign_repository as campaign_repository
from tesser.errors import not_found


@ts.do_not_use_function
def resolved_target(found: campaign_repository.FindCampaignResponse, slug: str) -> str:  # tesser:debt TB051
    match found.outcome:
        case campaign_repository.CampaignLookup.FOUND:
            return active_target(found.campaigns[0], slug)
        case campaign_repository.CampaignLookup.MISSING:
            raise not_found("link_missing", f"no active link for slug {slug!r}")
        case _ as unreachable:
            typing.assert_never(unreachable)


@ts.do_not_use_function
def active_target(record: campaign_repository.CampaignRecord, slug: str) -> str:  # tesser:debt TB051
    for link in record.links:
        if link.slug == slug and link.status == "active":
            return link.target_url
    raise not_found("link_missing", f"no active link for slug {slug!r}")
