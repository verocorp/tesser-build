"""Coordinate-driven impl selection (illustrated) + fail-fast. The "memory"
coordinate builds the in-memory repo; an ABSENT coordinate ERRORS at construction
— no path silently falls into volatile storage.
"""

from __future__ import annotations

import pytest

from bootstrap.bootstrap import new
from bootstrap.config import Config
from campaign.wiring.config import Config as CampaignConfig
from campaign.wiring.wire import repo_for as campaign_repo_for
from errors import DomainError
from linkpolicy.wiring.config import Config as LinkPolicyConfig
from linkpolicy.wiring.wire import repo_for as linkpolicy_repo_for
from reports.wiring.config import Config as ReportsConfig


def test_memory_coordinate_builds_and_is_its_own_closeable() -> None:
    repo, closeable = campaign_repo_for(CampaignConfig("memory"))
    assert id(repo) == id(closeable)  # the in-mem repo is its own closeable
    lp_repo, lp_closeable = linkpolicy_repo_for(LinkPolicyConfig("memory"))
    assert id(lp_repo) == id(lp_closeable)


def test_absent_coordinate_errors_not_silent_memory() -> None:
    with pytest.raises(DomainError):
        campaign_repo_for(CampaignConfig(""))
    with pytest.raises(DomainError):
        linkpolicy_repo_for(LinkPolicyConfig(""))


def test_bootstrap_fails_fast_on_absent_coordinate() -> None:
    with pytest.raises(DomainError):
        new(
            Config(
                campaign=CampaignConfig(""),
                linkpolicy=LinkPolicyConfig("memory"),
                reports=ReportsConfig(),
            )
        )
