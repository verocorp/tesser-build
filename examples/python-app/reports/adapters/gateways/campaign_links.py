from __future__ import annotations

import tesser.adapters as ts

import campaign.client
from reports.application.service import LinkFact


class CampaignLinkGateway(ts.Gateway):

    def __init__(self, links: campaign.client.Client) -> None:
        self._links = links

    def links(self) -> tuple[LinkFact, ...]:
        resp = self._links.list_links(campaign.client.ListLinksRequest())
        return tuple(LinkFact(slug=v.slug, target_url=v.target_url) for v in resp.links)
