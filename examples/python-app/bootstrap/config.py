"""The service-owned application ``Config`` — nested from each context's own
``wiring`` config. The toolkit prescribes the NESTING + per-context ownership; the
fields are the service's own (here, each context's coordinate). ``bootstrap`` hands
each context only its own slice.
"""

from __future__ import annotations

from dataclasses import dataclass

from campaign.wiring.config import Config as CampaignConfig
from linkpolicy.wiring.config import Config as LinkPolicyConfig


@dataclass(frozen=True)
class Config:
    campaign: CampaignConfig
    linkpolicy: LinkPolicyConfig
