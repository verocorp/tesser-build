from __future__ import annotations

from dataclasses import dataclass

from campaign.wiring.config import Config as CampaignConfig
from linkpolicy.wiring.config import Config as LinkPolicyConfig
from reports.wiring.config import Config as ReportsConfig


@dataclass(frozen=True)
class Config:
    campaign: CampaignConfig
    linkpolicy: LinkPolicyConfig
    reports: ReportsConfig
