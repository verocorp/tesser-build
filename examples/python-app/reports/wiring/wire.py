from __future__ import annotations

import tesser.context as ts

import campaign.client.client as campaign_client
from tesser.lifecycle import Closeable
import linkpolicy.client.client as linkpolicy_client
import reports.adapters.gateways.campaign_links as campaign_links
import reports.adapters.gateways.policy_verdicts as policy_verdicts
import reports.application.service as reports_service
import reports.client.client as client
import reports.wiring.config as config


class NoResources(ts.Wiring):

    def close(self) -> None:
        return None


@ts.function
def build(
    cfg: config.Config, campaign_client: campaign_client.Client, policy_client: linkpolicy_client.Client
) -> tuple[client.Client, Closeable]:
    service = reports_service.ReportsService(campaign_links.CampaignLinkGateway(campaign_client), policy_verdicts.PolicyVerdictGateway(policy_client))
    return service, NoResources()
