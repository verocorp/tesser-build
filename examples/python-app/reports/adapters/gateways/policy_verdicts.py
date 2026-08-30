from __future__ import annotations

import tesser.adapters as ts

import linkpolicy.client.client as linkpolicy_client
import reports.application.ports.verdict_source as verdict_source


class PolicyVerdictGateway(ts.Gateway):

    def __init__(self, verdicts: linkpolicy_client.Client) -> None:
        self._verdicts = verdicts

    def verdicts(self, request: verdict_source.ListVerdictsRequest) -> verdict_source.ListVerdictsResponse:
        resp = self._verdicts.list_verdicts(linkpolicy_client.ListVerdictsRequest())
        records = tuple(
            verdict_source.VerdictRecord(
                target_url=v.target_url,
                decision=verdict_source.VerdictDecision(v.decision),
                reason=v.reason,
            )
            for v in resp.verdicts
        )
        return verdict_source.ListVerdictsResponse(verdicts=records)
