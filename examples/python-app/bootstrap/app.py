from __future__ import annotations

import campaign.adapters.gateways.target_policy as target_policy
import campaign.client.client as campaign_client
import campaign.wiring.wire as campaign_wire
import linkpolicy.client.client as linkpolicy_client
import linkpolicy.wiring.wire as linkpolicy_wire
import reports.client.client as reports_client
import reports.wiring.wire as reports_wire
from tesser.lifecycle import Closeable

import bootstrap.config as config


class App:  # tessercheck:ignore TB051

    def __init__(self, cfg: config.Config) -> None:
        made: list[Closeable] = []
        try:
            policies = linkpolicy_wire.LinkPolicy(cfg.linkpolicy)
            made.append(policies)
            campaigns = campaign_wire.Campaign(
                cfg.campaign, target_policy.LinkPolicyTargetPolicy(policies.client)
            )
            made.append(campaigns)
            reports = reports_wire.Reports(cfg.reports, campaigns.client, policies.client)
            made.append(reports)
        except Exception:
            for built in made:
                built.close()
            raise
        self._components: tuple[Closeable, ...] = (policies, campaigns, reports)
        self.http: config.HttpConfig = cfg.http
        self.campaign: campaign_client.Client = campaigns.client
        self.linkpolicy: linkpolicy_client.Client = policies.client
        self.reports: reports_client.Client = reports.client

    def close(self) -> None:
        for built in self._components:
            built.close()
