from __future__ import annotations  # tessercheck:ignore TB050

from collections.abc import Mapping
from typing import Protocol

import campaign.wiring.config as campaign_config
import linkpolicy.wiring.config as linkpolicy_config
import reports.wiring.config as reports_config
from tesser.errors import invalid

import bootstrap.config as config


class ConfigRepository(Protocol):  # tessercheck:ignore TB051

    def get(self) -> config.Config: ...


class EnvConfigRepository:  # tessercheck:ignore TB051

    def __init__(self, env: Mapping[str, str]) -> None:
        self._env = env

    def get(self) -> config.Config:
        return config.Config(
            campaign=campaign_config.Config(storage=self._required("CAMPAIGN_STORAGE")),
            linkpolicy=linkpolicy_config.Config(storage=self._required("LINKPOLICY_STORAGE")),
            reports=reports_config.Config(),
            http=config.HttpConfig(
                host=self._required("HTTP_HOST"), port=self._port(self._required("HTTP_PORT"))
            ),
        )

    def _required(self, name: str) -> str:
        value = self._env.get(name)
        if value is None:
            raise invalid("missing_env", f"{name} is required")
        return value

    def _port(self, raw: str) -> int:
        try:
            return int(raw)
        except ValueError:
            raise invalid("bad_http_port", f"HTTP_PORT must be an integer, got {raw!r}") from None
