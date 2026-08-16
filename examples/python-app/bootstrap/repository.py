from __future__ import annotations

import os

import tesser.app as ts

import campaign.wiring.config as campaign_config
import linkpolicy.wiring.config as linkpolicy_config
import reports.wiring.config as reports_config
from tesser.errors import invalid

import bootstrap.config as config


class EnvConfigRepository(ts.ConfigRepository[config.Config]):

    def get(self) -> config.Config:
        return config.Config(
            config.Spec(
                campaign=campaign_config.Config(
                    campaign_config.Spec(storage=self._required("CAMPAIGN_STORAGE"))
                ),
                linkpolicy=linkpolicy_config.Config(
                    linkpolicy_config.Spec(storage=self._required("LINKPOLICY_STORAGE"))
                ),
                reports=reports_config.Config(reports_config.Spec()),
                http=config.HttpConfig(
                    config.HttpSpec(
                        host=self._required("HTTP_HOST"),
                        port=self._port(self._required("HTTP_PORT")),
                    )
                ),
            )
        )

    def _required(self, name: str) -> str:
        value = os.environ.get(name)
        if value is None:
            raise invalid("missing_env", f"{name} is required")
        return value

    def _port(self, raw: str) -> int:
        try:
            return int(raw)
        except ValueError:
            raise invalid("bad_http_port", f"HTTP_PORT must be an integer, got {raw!r}") from None
