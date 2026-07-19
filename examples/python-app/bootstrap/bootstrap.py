from __future__ import annotations

import campaign
import campaign.wiring.wire as campaign_wire
import linkpolicy
import linkpolicy.wiring.wire as linkpolicy_wire
import reports
import reports.wiring.wire as reports_wire
from bootstrap.config import Config
from campaign.adapters.gateways.target_checker import LinkPolicyTargetChecker
from lifecycle import Closeable


class CleanupStack:

    def __init__(self) -> None:
        self._resources: list[Closeable] = []

    def push(self, resource: Closeable) -> None:
        self._resources.append(resource)

    def close_all(self) -> list[Exception]:
        errors: list[Exception] = []
        while self._resources:
            resource = self._resources.pop()
            try:
                resource.close()
            except Exception as e:
                errors.append(e)
        return errors


class App:

    def __init__(
        self,
        campaign_client: campaign.Client,
        policy_client: linkpolicy.Client,
        reports_client: reports.Client,
        stack: CleanupStack,
    ) -> None:
        self.campaign = campaign_client
        self.linkpolicy = policy_client
        self.reports = reports_client
        self._stack = stack
        self._closed = False

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._stack.close_all()


def new(cfg: Config) -> App:
    stack = CleanupStack()
    try:
        policy_client, policy_closeable = linkpolicy_wire.build(cfg.linkpolicy)
        stack.push(policy_closeable)

        checker = LinkPolicyTargetChecker(policy_client)
        campaign_client, campaign_closeable = campaign_wire.build(cfg.campaign, checker)
        stack.push(campaign_closeable)

        reports_client, reports_closeable = reports_wire.build(cfg.reports, campaign_client, policy_client)
        stack.push(reports_closeable)
        return App(campaign_client, policy_client, reports_client, stack)
    except Exception:
        stack.close_all()
        raise
