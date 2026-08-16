from __future__ import annotations

import tesser.context as ts

import campaign.client.client as campaign_client
import linkpolicy.client.client as linkpolicy_client
import reports.adapters.gateways.campaign_links as campaign_links
import reports.adapters.gateways.policy_verdicts as policy_verdicts
import reports.application.service as reports_service
import reports.client.client as client
import reports.wiring.config as config


class Reports(ts.Wiring):

    def __init__(
        self, cfg: config.Config, campaigns: campaign_client.Client, policies: linkpolicy_client.Client
    ) -> None:
        self.client: client.Client = reports_service.ReportsService(
            campaign_links.CampaignLinkGateway(campaigns), policy_verdicts.PolicyVerdictGateway(policies)
        )

    def close(self) -> None:
        return None
