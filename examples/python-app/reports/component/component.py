from __future__ import annotations

import tesser.component as ts

import campaign.client as campaign_client
import linkpolicy.client as linkpolicy_client
import reports.adapters.gateways as gateways
import reports.application as application
import reports.client as client


class Spec(ts.Spec):

    def __init__(self) -> None:
        return None


class Config(ts.Config):

    def __init__(self, spec: Spec) -> None:
        return None


class Reports(ts.Component):

    def __init__(
        self,
        config: Config,
        campaign_client: campaign_client.CampaignClient,
        link_policy_client: linkpolicy_client.LinkPolicyClient,
    ) -> None:
        self.client: client.ReportsClient = application.ReportsService(
            gateways.CampaignLinkGateway(campaign_client),
            gateways.PolicyVerdictGateway(link_policy_client),
        )

    def close(self) -> None:
        return None
