from __future__ import annotations

import tesser.app as ts

import campaign.adapters.gateways.target_policy as target_policy
import campaign.component.component as campaign_component
import linkpolicy.component.component as linkpolicy_component
import reports.component.component as reports_component

import app.config as config


class App(ts.App):

    def __init__(self, cfg: config.Config) -> None:
        linkpolicy = linkpolicy_component.LinkPolicy(cfg.linkpolicy)
        try:
            campaign = campaign_component.Campaign(
                cfg.campaign, target_policy.LinkPolicyTargetPolicy(linkpolicy.client)
            )
        except Exception:
            linkpolicy.close()
            raise
        try:
            reports = reports_component.Reports(cfg.reports, campaign.client, linkpolicy.client)
        except Exception:
            campaign.close()
            linkpolicy.close()
            raise
        self.linkpolicy = linkpolicy
        self.campaign = campaign
        self.reports = reports
        self.http = cfg.http

    def close(self) -> None:
        self.reports.close()
        self.campaign.close()
        self.linkpolicy.close()
