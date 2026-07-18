"""linkpolicy's construction: pick the repo from the coordinate, compose the
service behind the public ``Client``, and hand back the closeable so the
composition root can register it on its cleanup stack.

Coordinate-driven impl selection (decision 8, illustrated): ``storage == "memory"``
builds the in-memory repo; an ABSENT coordinate is an ERROR, never a silent fall
into volatile storage. A real service would map a DSN scheme to a SQL repo here.
"""

from __future__ import annotations

from errors import invalid
from lifecycle import Closeable
from linkpolicy.adapters.gateways.repo_memory import InMemoryVerdictRepository
from linkpolicy.application.service import LinkPolicyService, VerdictRepository
from linkpolicy.client import Client
from linkpolicy.domain.policy import Policy
from linkpolicy.wiring.config import Config


def repo_for(cfg: Config) -> tuple[VerdictRepository, Closeable]:
    if cfg.storage == "memory":
        repo = InMemoryVerdictRepository()
        return repo, repo
    if not cfg.storage:
        raise invalid("missing_coordinate", "linkpolicy storage coordinate is required")
    raise invalid("unknown_backend", f"linkpolicy storage {cfg.storage!r} not supported")


def build(cfg: Config) -> tuple[Client, Closeable]:
    """Return the public ``Client`` and the closeable resource behind it."""
    repo, closeable = repo_for(cfg)
    service = LinkPolicyService(repo, Policy.default())
    return service, closeable
