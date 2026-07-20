from __future__ import annotations

import os
import sys

from bootstrap.bootstrap import new
from bootstrap.config import Config
from campaign.client import AddLinkRequest, CreateCampaignRequest
from campaign.wiring.config import Config as CampaignConfig
from linkpolicy.wiring.config import Config as LinkPolicyConfig
from reports.wiring.config import Config as ReportsConfig

_USAGE = (
    "usage: python -m srv.cli.main create-campaign <budget_amount> <currency>\n"
    "       python -m srv.cli.main add-link <campaign_id> <slug> <target_url>"
)


def run(argv: list[str]) -> int:
    cfg = Config(
        campaign=CampaignConfig(storage=os.getenv("CAMPAIGN_STORAGE") or ""),
        linkpolicy=LinkPolicyConfig(storage=os.getenv("LINKPOLICY_STORAGE") or ""),
        reports=ReportsConfig(),
    )
    app = new(cfg)
    try:
        if len(argv) == 3 and argv[0] == "create-campaign":
            view = app.campaign.create_campaign(
                CreateCampaignRequest(budget_amount=argv[1], budget_currency=argv[2])
            )
            print(f"created campaign {view.campaign_id} with budget {view.budget_amount} {view.budget_currency}")  # noqa: T201
            return 0
        if len(argv) == 4 and argv[0] == "add-link":
            view = app.campaign.add_link(
                AddLinkRequest(campaign_id=argv[1], slug=argv[2], target_url=argv[3])
            )
            print(f"campaign {view.campaign_id} now has {len(view.links)} link(s)")  # noqa: T201
            return 0
        print(_USAGE)  # noqa: T201
        return 2
    finally:
        app.close()


if __name__ == "__main__":
    raise SystemExit(run(sys.argv[1:]))
