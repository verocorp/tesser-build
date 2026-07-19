from __future__ import annotations

import campaign
import linkpolicy
from reports.client import LinkVerdictView
from reports.domain.report import Link, RecordedVerdict, join_links_with_verdicts


class ReportsService:
    def __init__(self, campaign_client: campaign.Client, policy_client: linkpolicy.Client) -> None:
        self._campaign = campaign_client
        self._policy = policy_client

    def links_by_verdict(self) -> tuple[LinkVerdictView, ...]:
        links = tuple(Link(slug=l.slug, target_url=l.target_url) for l in self._campaign.list_links())
        verdicts = tuple(
            RecordedVerdict(target_url=v.target_url, allowed=v.allowed, reason=v.reason)
            for v in self._policy.list_verdicts()
        )
        return tuple(
            LinkVerdictView(slug=r.slug, target_url=r.target_url, allowed=r.allowed, reason=r.reason)
            for r in join_links_with_verdicts(links, verdicts)
        )
