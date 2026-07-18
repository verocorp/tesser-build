"""reports' construction: compose the service over the two injected peer
``Client``s and hand back the closeable so the composition root can register it
on its cleanup stack — the same build seam as every sibling.

``build`` takes the peer Clients as parameters — reports does not construct its
peers; the composition root builds them first and injects them here (dependency
direction: reports sits above both).
"""

from __future__ import annotations

import campaign
import linkpolicy
from lifecycle import Closeable
from reports.application.service import ReportsService
from reports.client import Client
from reports.wiring.config import Config


class _NoResources:
    """reports holds no closeable resources today; this stand-in keeps the build
    seam uniform (Client + Closeable) so the cleanup stack treats reports like
    any sibling. A real read-model cache's pool would take its place."""

    def close(self) -> None:
        return None


def build(
    cfg: Config, campaign_client: campaign.Client, policy_client: linkpolicy.Client
) -> tuple[Client, Closeable]:
    """Return the public ``Client`` and the closeable resource behind it."""
    return ReportsService(campaign_client, policy_client), _NoResources()
