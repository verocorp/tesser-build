"""The reports application service: fetch from both peers, translate their DTOs
into the domain's vocabulary, delegate the join to the domain, respond with the
public DTOs. It satisfies ``reports.Client`` structurally, so ``wiring`` can
return it directly as the public Client.

reports reaches its peers only through their public ``Client``s, injected by
the composition root — it never constructs a peer. That is why this context
needs no adapters of its own (OQ5 ruling: adapters are optional).
"""

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
