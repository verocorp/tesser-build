from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from campaign.wiring.config import Config as CampaignConfig
from errors import invalid
from linkpolicy.wiring.config import Config as LinkPolicyConfig
from reports.wiring.config import Config as ReportsConfig

Getenv = Callable[[str], Optional[str]]


@dataclass(frozen=True)
class HttpConfig:
    host: str
    port: int


@dataclass(frozen=True)
class Config:
    campaign: CampaignConfig
    linkpolicy: LinkPolicyConfig
    reports: ReportsConfig
    http: HttpConfig = HttpConfig("", 8080)


def _port(raw: Optional[str]) -> int:
    text = raw or "8080"
    try:
        return int(text)
    except ValueError:
        raise invalid("bad_http_port", f"HTTP_PORT must be an integer, got {text!r}") from None


def from_env(getenv: Getenv) -> Config:
    return Config(
        campaign=CampaignConfig(storage=getenv("CAMPAIGN_STORAGE") or ""),
        linkpolicy=LinkPolicyConfig(storage=getenv("LINKPOLICY_STORAGE") or ""),
        reports=ReportsConfig(),
        http=HttpConfig(host=getenv("HTTP_HOST") or "", port=_port(getenv("HTTP_PORT"))),
    )
