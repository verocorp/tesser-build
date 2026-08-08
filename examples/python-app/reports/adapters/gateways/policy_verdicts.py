from __future__ import annotations

import tesser.adapters as ts

import linkpolicy.client.client as linkpolicy_client
from reports.application.service import VerdictFact


class PolicyVerdictGateway(ts.Gateway):

    def __init__(self, verdicts: linkpolicy_client.Client) -> None:
        self._verdicts = verdicts

    def verdicts(self) -> tuple[VerdictFact, ...]:
        resp = self._verdicts.list_verdicts(linkpolicy_client.ListVerdictsRequest())
        return tuple(VerdictFact(v.target_url, v.allowed, v.reason) for v in resp.verdicts)
