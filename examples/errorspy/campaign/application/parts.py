from __future__ import annotations

import tesser.application as ts

import campaign.domain.campaign as campaign
import campaign.domain.short_link as short_link


class LinkParts(ts.Parts):

    def __init__(self, slug: str, target_url: str) -> None:
        self.slug = slug
        self.target_url = target_url


class WindowParts(ts.Parts):

    def __init__(self, start: str, end: str) -> None:
        self.start = start
        self.end = end


class CampaignParts(ts.Parts):

    def __init__(self, id: str, window: WindowParts, links: tuple[LinkParts, ...]) -> None:
        self.id = id
        self.window = window
        self.links = links


class FoundCampaign(ts.Parts):

    def __init__(self, parts: CampaignParts) -> None:
        self.parts = parts


class MissingCampaign(ts.Parts):

    def __init__(self) -> None:
        return None


@ts.function
def campaign_parts(c: campaign.Campaign) -> CampaignParts:
    return CampaignParts(
        id=c.id,
        window=WindowParts(start=str(c.window.start), end=str(c.window.end)),
        links=tuple(link_parts(link) for link in c.links),
    )


@ts.function
def link_parts(link: short_link.ShortLink) -> LinkParts:
    return LinkParts(slug=str(link.slug), target_url=str(link.target))
