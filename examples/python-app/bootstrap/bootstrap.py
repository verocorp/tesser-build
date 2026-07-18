"""The composition root: service-owned, source-agnostic. ``new(cfg)`` validates
the config, builds the object graph ONCE, and returns an ``App`` with ``close()``.
It reads no environment (the host is the env edge: each ``srv/*/main`` populates
``cfg`` and passes it in).

Two things the governing rule makes required correctness (not machinery):
  - It builds each closeable onto a CLEANUP STACK; if a later dep fails, the
    already-built ones are closed before the error propagates — no leak.
  - As the composition root it is the one place allowed to know every concrete
    (it constructs campaign's cross-context adapter over ``linkpolicy.Client`` and
    injects it), which a context never does to another context.
"""

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
    """Closeables in construction order; closed in REVERSE on teardown. A close
    that raises does not stop the others — every resource gets a close attempt and
    the errors are collected."""

    def __init__(self) -> None:
        self._resources: list[Closeable] = []

    def push(self, resource: Closeable) -> None:
        self._resources.append(resource)

    def close_all(self) -> list[Exception]:
        errors: list[Exception] = []
        while self._resources:
            resource = self._resources.pop()  # reverse order
            try:
                resource.close()
            except Exception as e:  # keep going; a leaky close must not orphan the rest
                errors.append(e)
        return errors


class App:
    """The built graph. Holds the three contexts' public Clients, and owns
    teardown via ``close()`` (idempotent — the single lifecycle method the template
    mandates; graceful-shutdown ordering is the host's fill-in)."""

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

        # campaign's cross-context adapter, constructed HERE (composition root) and
        # injected — campaign never imports linkpolicy itself.
        checker = LinkPolicyTargetChecker(policy_client)
        campaign_client, campaign_closeable = campaign_wire.build(cfg.campaign, checker)
        stack.push(campaign_closeable)

        # reports sits above both peers: built last, with their Clients injected.
        reports_client, reports_closeable = reports_wire.build(cfg.reports, campaign_client, policy_client)
        stack.push(reports_closeable)
        return App(campaign_client, policy_client, reports_client, stack)
    except Exception:
        stack.close_all()  # partial-construction cleanup: close what was built
        raise
