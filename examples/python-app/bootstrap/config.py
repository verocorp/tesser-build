from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

import campaign.wiring.config as config
from tesser.errors import invalid
import linkpolicy.wiring.config as linkpolicy_config
import reports.wiring.config as reports_config

import tesser.context as ts

Getenv = Callable[[str], Optional[str]]  # tessercheck:ignore TB051


@dataclass(frozen=True)
class HttpConfig:  # tessercheck:ignore TB051
    host: str
    port: int


@dataclass(frozen=True)
class Config:  # tessercheck:ignore TB051
    campaign: config.Config
    linkpolicy: linkpolicy_config.Config
    reports: reports_config.Config
    http: HttpConfig = HttpConfig("", 8080)


@ts.function
def _port(raw: Optional[str]) -> int:
    text = raw or "8080"
    try:
        return int(text)
    except ValueError:
        raise invalid("bad_http_port", f"HTTP_PORT must be an integer, got {text!r}") from None


@ts.function
def from_env(getenv: Getenv) -> Config:
    return Config(
        campaign=config.Config(storage=getenv("CAMPAIGN_STORAGE") or ""),
        linkpolicy=linkpolicy_config.Config(storage=getenv("LINKPOLICY_STORAGE") or ""),
        reports=reports_config.Config(),
        http=HttpConfig(host=getenv("HTTP_HOST") or "", port=_port(getenv("HTTP_PORT"))),
    )
