from __future__ import annotations

import os
import typing

import tesser.app as ts

import campaign.adapters.gateways as campaign_gateways
import campaign.component as campaign_component
import linkpolicy.component as linkpolicy_component
import reports.component as reports_component
import tesser.errors as errors


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
        campaign: campaign_component.Config,
        linkpolicy: linkpolicy_component.Config,
        reports: reports_component.Config,
        http: HttpConfig,
    ) -> None:
        self.campaign = campaign
        self.linkpolicy = linkpolicy
        self.reports = reports
        self.http = http


class AppConfig(ts.Config):

    def __init__(self, spec: Spec) -> None:
        self.campaign = spec.campaign
        self.linkpolicy = spec.linkpolicy
        self.reports = spec.reports
        self.http = spec.http


class PythonApp(ts.App):

    def __init__(self, app_config: AppConfig) -> None:
        link_policy = linkpolicy_component.LinkPolicy(app_config.linkpolicy)
        try:
            campaign = campaign_component.Campaign(
                app_config.campaign, campaign_gateways.LinkPolicyTargetPolicy(link_policy.client)
            )
        except Exception:
            link_policy.close()
            raise
        try:
            reports = reports_component.Reports(
                app_config.reports, campaign.client, link_policy.client
            )
        except Exception:
            campaign.close()
            link_policy.close()
            raise
        self.linkpolicy = link_policy
        self.campaign = campaign
        self.reports = reports
        self.http = app_config.http

    def close(self) -> None:
        self.reports.close()
        self.campaign.close()
        self.linkpolicy.close()


class AppConfigRepository(ts.ConfigRepository, typing.Protocol):

    def get(self) -> AppConfig: ...


class EnvConfigRepository(AppConfigRepository):

    def get(self) -> AppConfig:
        campaign_storage = os.environ.get("CAMPAIGN_STORAGE")
        if campaign_storage is None:
            raise errors.invalid("missing_env", "CAMPAIGN_STORAGE is required")
        linkpolicy_storage = os.environ.get("LINKPOLICY_STORAGE")
        if linkpolicy_storage is None:
            raise errors.invalid("missing_env", "LINKPOLICY_STORAGE is required")
        http_host = os.environ.get("HTTP_HOST")
        if http_host is None:
            raise errors.invalid("missing_env", "HTTP_HOST is required")
        raw_port = os.environ.get("HTTP_PORT")
        if raw_port is None:
            raise errors.invalid("missing_env", "HTTP_PORT is required")
        try:
            http_port = int(raw_port)
        except ValueError:
            raise errors.invalid("bad_http_port", f"HTTP_PORT must be an integer, got {raw_port!r}") from None
        return AppConfig(
            Spec(
                campaign=campaign_component.Config(
                    campaign_component.Spec(storage=campaign_storage)
                ),
                linkpolicy=linkpolicy_component.Config(
                    linkpolicy_component.Spec(storage=linkpolicy_storage)
                ),
                reports=reports_component.Config(reports_component.Spec()),
                http=HttpConfig(HttpSpec(host=http_host, port=http_port)),
            )
        )


class AppLoader(ts.Loader):

    def __init__(self, app_config_repository: AppConfigRepository) -> None:
        self._app_config_repository = app_config_repository

    def load(self) -> PythonApp:
        return PythonApp(self._app_config_repository.get())


@ts.load
def load() -> PythonApp:
    return AppLoader(EnvConfigRepository()).load()
