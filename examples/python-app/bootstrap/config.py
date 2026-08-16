from __future__ import annotations

import tesser.app as ts

import campaign.wiring.config as campaign_config
import linkpolicy.wiring.config as linkpolicy_config
import reports.wiring.config as reports_config


class HttpSpec(ts.Spec):

    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port


class HttpConfig(ts.Config):

    def __init__(self, spec: HttpSpec) -> None:
        self.host = spec.host
        self.port = spec.port


class Spec(ts.Spec):

    def __init__(
        self,
        campaign: campaign_config.Config,
        linkpolicy: linkpolicy_config.Config,
        reports: reports_config.Config,
        http: HttpConfig,
    ) -> None:
        self.campaign = campaign
        self.linkpolicy = linkpolicy
        self.reports = reports
        self.http = http


class Config(ts.Config):

    def __init__(self, spec: Spec) -> None:
        self.campaign = spec.campaign
        self.linkpolicy = spec.linkpolicy
        self.reports = spec.reports
        self.http = spec.http
