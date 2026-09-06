from __future__ import annotations

import tesser.adapters as ts

import campaign.client as client
import reports.application.ports as ports


class CampaignLinkGateway(ts.Gateway):

    def __init__(self, campaign_client: client.CampaignClient) -> None:
        self._campaign_client = campaign_client

    def links(self, list_links_request: ports.ListLinksRequest) -> ports.ListLinksResponse:
        list_links_response = self._campaign_client.list_links(client.ListLinksRequest())
        return ports.ListLinksResponse(
            links=tuple(
                ports.LinkRecord(slug=v.slug, target_url=v.target_url)
                for v in list_links_response.links
            )
        )
