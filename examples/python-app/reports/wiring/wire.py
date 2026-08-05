from __future__ import annotations

import campaign.client
import linkpolicy.client
from lifecycle import Closeable
from reports.application.service import ReportsService
from reports.client import Client
from reports.wiring.config import Config


class _NoResources:

    def close(self) -> None:
        return None


def build(
    cfg: Config, campaign_client: campaign.client.Client, policy_client: linkpolicy.client.Client
) -> tuple[Client, Closeable]:
    return ReportsService(campaign_client, policy_client), _NoResources()
