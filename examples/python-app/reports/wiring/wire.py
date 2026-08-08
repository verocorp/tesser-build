from __future__ import annotations

import tesser.context as ts

import campaign.client.client as campaign_client
import linkpolicy.client.client as linkpolicy_client
from lifecycle import Closeable
from reports.adapters.gateways.campaign_links import CampaignLinkGateway
from reports.adapters.gateways.policy_verdicts import PolicyVerdictGateway
from reports.application.service import ReportsService
from reports.client.client import Client
from reports.wiring.config import Config


class NoResources(ts.Wiring):

    def close(self) -> None:
        return None


@ts.function
def build(
    cfg: Config, campaign_client: campaign_client.Client, policy_client: linkpolicy_client.Client
) -> tuple[Client, Closeable]:
    service = ReportsService(CampaignLinkGateway(campaign_client), PolicyVerdictGateway(policy_client))
    return service, NoResources()
