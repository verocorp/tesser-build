from __future__ import annotations

import os

from typing import Protocol

import tesser.app as ts

import campaign.component.config as campaign_config
import linkpolicy.component.config as linkpolicy_config
import reports.component.config as reports_config
from tesser.errors import invalid

import app.config as config


class ConfigRepository(ts.ConfigRepository, Protocol):

    def get(self) -> config.Config: ...


class EnvConfigRepository(ConfigRepository):

    def get(self) -> config.Config:
        campaign_storage = os.environ.get("CAMPAIGN_STORAGE")
        if campaign_storage is None:
            raise invalid("missing_env", "CAMPAIGN_STORAGE is required")
        linkpolicy_storage = os.environ.get("LINKPOLICY_STORAGE")
        if linkpolicy_storage is None:
            raise invalid("missing_env", "LINKPOLICY_STORAGE is required")
        http_host = os.environ.get("HTTP_HOST")
        if http_host is None:
            raise invalid("missing_env", "HTTP_HOST is required")
        raw_port = os.environ.get("HTTP_PORT")
        if raw_port is None:
            raise invalid("missing_env", "HTTP_PORT is required")
        try:
            http_port = int(raw_port)
        except ValueError:
            raise invalid("bad_http_port", f"HTTP_PORT must be an integer, got {raw_port!r}") from None
        return config.Config(
            config.Spec(
                campaign=campaign_config.Config(
                    campaign_config.Spec(storage=campaign_storage)
                ),
                linkpolicy=linkpolicy_config.Config(
                    linkpolicy_config.Spec(storage=linkpolicy_storage)
                ),
                reports=reports_config.Config(reports_config.Spec()),
                http=config.HttpConfig(
                    config.HttpSpec(host=http_host, port=http_port)
                ),
            )
        )
