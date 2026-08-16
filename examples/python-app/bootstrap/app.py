from __future__ import annotations  # tessercheck:ignore TB050

import campaign.adapters.gateways.target_policy as target_policy
import campaign.wiring.wire as campaign_wire
import linkpolicy.wiring.wire as linkpolicy_wire
import reports.wiring.wire as reports_wire

import bootstrap.config as config


class App:  # tessercheck:ignore TB051

    def __init__(self, cfg: config.Config) -> None:
        linkpolicy = linkpolicy_wire.LinkPolicy(cfg.linkpolicy)
        try:
            campaign = campaign_wire.Campaign(
                cfg.campaign, target_policy.LinkPolicyTargetPolicy(linkpolicy.client)
            )
        except Exception:
            linkpolicy.close()
            raise
        try:
            reports = reports_wire.Reports(cfg.reports, campaign.client, linkpolicy.client)
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
