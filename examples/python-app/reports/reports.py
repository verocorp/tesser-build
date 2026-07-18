"""The cross-context read: "links by policy verdict". Needs the link/target
(campaign) and the recorded verdict (linkpolicy); belongs to neither context.
"""

from __future__ import annotations

from dataclasses import dataclass

import campaign
import linkpolicy


@dataclass(frozen=True)
class LinkVerdictRow:
    slug: str
    target_url: str
    allowed: bool
    reason: str


class ReportsService:
    def __init__(self, campaign_client: campaign.Client, policy_client: linkpolicy.Client) -> None:
        self._campaign = campaign_client
        self._policy = policy_client

    def links_by_verdict(self) -> tuple[LinkVerdictRow, ...]:
        verdicts = {v.target_url: v for v in self._policy.list_verdicts()}
        rows = [
            LinkVerdictRow(
                slug=link.slug,
                target_url=link.target_url,
                allowed=verdicts[link.target_url].allowed if link.target_url in verdicts else True,
                reason=verdicts[link.target_url].reason if link.target_url in verdicts else "no verdict recorded",
            )
            for link in self._campaign.list_links()
        ]
        return tuple(sorted(rows, key=lambda r: (r.allowed, r.slug)))
