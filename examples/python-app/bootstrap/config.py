from __future__ import annotations

import campaign.wiring.config as campaign_config
import linkpolicy.wiring.config as linkpolicy_config
import reports.wiring.config as reports_config


class HttpConfig:  # tessercheck:ignore TB051

    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port


class Config:  # tessercheck:ignore TB051

    def __init__(
        self,
        campaign: campaign_config.Config,
        linkpolicy: linkpolicy_config.Config,
        reports: reports_config.Config,
        http: HttpConfig,
    ) -> None:
        self.http = http
        self.campaign = campaign
        self.linkpolicy = linkpolicy
        self.reports = reports
