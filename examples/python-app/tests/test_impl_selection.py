from __future__ import annotations

import pytest

from bootstrap.bootstrap import new
from bootstrap.config import Config
import campaign.wiring.config as config
import campaign.wiring.wire as wire
from errors import DomainError
import linkpolicy.wiring.config as linkpolicy_config
import linkpolicy.wiring.wire as linkpolicy_wire
import reports.wiring.config as reports_config


def test_memory_coordinate_builds_and_is_its_own_closeable() -> None:
    repo, closeable = wire.repo_for(config.Config("memory"))
    assert id(repo) == id(closeable)
    lp_repo, lp_closeable = linkpolicy_wire.repo_for(linkpolicy_config.Config("memory"))
    assert id(lp_repo) == id(lp_closeable)


def test_absent_coordinate_errors_not_silent_memory() -> None:
    with pytest.raises(DomainError):
        wire.repo_for(config.Config(""))
    with pytest.raises(DomainError):
        linkpolicy_wire.repo_for(linkpolicy_config.Config(""))


def test_bootstrap_fails_fast_on_absent_coordinate() -> None:
    with pytest.raises(DomainError):
        new(
            Config(
                campaign=config.Config(""),
                linkpolicy=linkpolicy_config.Config("memory"),
                reports=reports_config.Config(),
            )
        )
