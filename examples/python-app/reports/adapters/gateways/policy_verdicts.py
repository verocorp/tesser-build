from __future__ import annotations

import tesser.adapters as ts

import linkpolicy.client.client as linkpolicy_client
import reports.application.service as service


class PolicyVerdictGateway(ts.Gateway):

    def __init__(self, verdicts: linkpolicy_client.Client) -> None:
        self._verdicts = verdicts

    def verdicts(self) -> tuple[service.VerdictFact, ...]:
        resp = self._verdicts.list_verdicts(linkpolicy_client.ListVerdictsRequest())
        return tuple(service.VerdictFact(v.target_url, v.allowed, v.reason) for v in resp.verdicts)
