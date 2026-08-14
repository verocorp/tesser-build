from __future__ import annotations

import tesser.adapters as ts

import campaign.client.client as campaign_client
import reports.application.ports.link_source as link_source


class CampaignLinkGateway(ts.Gateway):

    def __init__(self, links: campaign_client.Client) -> None:
        self._links = links

    def links(self, request: link_source.ListLinksRequest) -> link_source.ListLinksResponse:
        resp = self._links.list_links(campaign_client.ListLinksRequest())
        return link_source.ListLinksResponse(
            links=tuple(link_source.LinkRecord(slug=v.slug, target_url=v.target_url) for v in resp.links)
        )
