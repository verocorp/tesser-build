from __future__ import annotations

import tesser.adapters as ts

import campaign.client as campaign_client
import reports.application.ports as ports


class CampaignLinkGateway(ts.Gateway):

    def __init__(self, campaign_client: campaign_client.CampaignClient) -> None:
        self._campaign_client = campaign_client

    def links(self, list_links_request: ports.ListLinksRequest) -> ports.ListLinksResponse:
        try:
            list_links_response = self._campaign_client.list_links(campaign_client.ListLinksRequest())
        except campaign_client.Unavailable as campaign_error:
            raise ports.LinkSourceUnavailable(campaign_error.message) from campaign_error
        return ports.ListLinksResponse(
            links=tuple(
                ports.LinkRecord(slug=v.slug, target_url=v.target_url)
                for v in list_links_response.links
            )
        )
