from __future__ import annotations

import typing

import tesser.application as ts

import campaign.application.ports.campaign_repository as campaign_repository
import campaign.application.ports.target_policy as target_policy
import campaign.client.client as client
import campaign.domain.campaign as campaign
import campaign.domain.money as money
import campaign.domain.short_link as short_link
import campaign.domain.short_links as short_links
from tesser.errors import conflict, not_found


@ts.do_not_use_function
def campaign_view(c: campaign.Campaign) -> client.CampaignView:  # tesser:debt TB051
    return client.CampaignView(
        campaign_id=str(c.id),
        budget_amount=str(c.budget.amount),
        budget_currency=str(c.budget.currency),
        links=tuple(_domain_link_view(link) for link in c.links),
    )


@ts.do_not_use_function
def _domain_link_view(link: short_link.ShortLink) -> client.LinkView:  # tesser:debt TB051
    return client.LinkView(
        slug=str(link.slug), target_url=str(link.target_url), status=str(link.status)
    )


@ts.do_not_use_function
def link_view(record: campaign_repository.LinkRecord) -> client.LinkView:  # tesser:debt TB051
    return client.LinkView(
        slug=record.slug,
        target_url=record.target_url,
        status=record.status,
    )


@ts.do_not_use_function
def save_request(c: campaign.Campaign) -> campaign_repository.SaveCampaignRequest:  # tesser:debt TB051
    return campaign_repository.SaveCampaignRequest(
        id=str(c.id),
        budget=_money_record(c),
        links=tuple(_link_record(link) for link in c.links),
    )


@ts.do_not_use_function
def _money_record(c: campaign.Campaign) -> campaign_repository.MoneyRecord:  # tesser:debt TB051
    return campaign_repository.MoneyRecord(amount=str(c.budget.amount), currency=str(c.budget.currency))


@ts.do_not_use_function
def _link_record(link: short_link.ShortLink) -> campaign_repository.LinkRecord:  # tesser:debt TB051
    return campaign_repository.LinkRecord(
        slug=str(link.slug), target_url=str(link.target_url), status=str(link.status)
    )


@ts.do_not_use_function
def campaign_spec(record: campaign_repository.CampaignRecord) -> campaign.CampaignSpec:  # tesser:debt TB051
    return campaign.CampaignSpec(
        id=record.id,
        budget=money.MoneySpec(amount=record.budget.amount, currency=record.budget.currency),
        links=short_links.ShortLinksSpec(
            links=tuple(
                short_link.ShortLinkSpec(
                    slug=link.slug,
                    target_url=link.target_url,
                    active=link.status == "active",
                )
                for link in record.links
            )
        ),
    )


@ts.do_not_use_function
def required_campaign(  # tesser:debt TB051
    found: campaign_repository.FindCampaignResponse, campaign_id: str
) -> campaign.Campaign:
    match found.outcome:
        case campaign_repository.CampaignLookup.FOUND:
            return campaign.Campaign(campaign_spec(found.campaigns[0]))
        case campaign_repository.CampaignLookup.MISSING:
            raise not_found("campaign_missing", f"no campaign with id {campaign_id!r}")
        case _ as unreachable:
            typing.assert_never(unreachable)


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


@ts.do_not_use_function
def ensure_target_allowed(checked: target_policy.CheckTargetResponse) -> None:  # tesser:debt TB051
    match checked.verdict:
        case target_policy.PolicyVerdict.ALLOWED:
            return None
        case target_policy.PolicyVerdict.BLOCKED:
            raise conflict("destination_blocked", f"destination not allowed: {checked.reason}")
        case _ as unreachable:
            typing.assert_never(unreachable)


@ts.do_not_use_function
def ensure_slug_available(checked: campaign_repository.SlugTakenResponse, slug: str) -> None:  # tesser:debt TB051
    match checked.availability:
        case campaign_repository.SlugAvailability.FREE:
            return None
        case campaign_repository.SlugAvailability.TAKEN:
            raise conflict("duplicate_slug", f"slug {slug!r} already exists")
        case _ as unreachable:
            typing.assert_never(unreachable)
