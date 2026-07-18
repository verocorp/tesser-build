"""The CLI host (delivery mechanism 2). Same composition root, different edge: it
populates the spec-shaped ``Config`` with ``os.getenv`` calls (the host is the env
edge), calls ``bootstrap.new`` ONCE, and runs a self-contained ``create-link``
command against its OWN ``App`` (a real write — Moment 1 vets the destination). It
is a separate process from the http host and does NOT share its state; that is why
the reports read is demonstrated in-process, not across hosts.
"""

from __future__ import annotations

import os
import sys

from bootstrap.bootstrap import new
from bootstrap.config import Config
from campaign.client import CreateLinkRequest
from campaign.wiring.config import Config as CampaignConfig
from linkpolicy.wiring.config import Config as LinkPolicyConfig
from reports.wiring.config import Config as ReportsConfig


def run(argv: list[str]) -> int:
    cfg = Config(
        campaign=CampaignConfig(storage=os.getenv("CAMPAIGN_STORAGE") or ""),
        linkpolicy=LinkPolicyConfig(storage=os.getenv("LINKPOLICY_STORAGE") or ""),
        reports=ReportsConfig(),
    )
    app = new(cfg)  # graph built once; validates the coordinates fail-fast
    try:
        if len(argv) != 3 or argv[0] != "create-link":
            print("usage: python -m srv.cli.main create-link <slug> <target_url>")  # noqa: T201
            return 2
        resp = app.campaign.create_link(CreateLinkRequest(slug=argv[1], target_url=argv[2]))
        print(f"created {resp.slug} -> {resp.target_url}")  # noqa: T201
        return 0
    finally:
        app.close()


if __name__ == "__main__":
    raise SystemExit(run(sys.argv[1:]))
