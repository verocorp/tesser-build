"""The lifecycle seam shared by the composition root and the contexts' wiring.

``Closeable`` is the minimal shape ``bootstrap`` needs to tear a graph down: a
resource the cleanup stack can close (a DB pool, a client, a repository holding
one). In-memory repos implement it as a near-no-op; a real service's SQL repo
closes its pool here. This is the ONLY lifecycle contract the template mandates
(governing rule: minimal) — graceful-shutdown ordering, drain, and readiness are
the host's fill-in and are deliberately not modelled here.
"""

from __future__ import annotations

from typing import Protocol


class Closeable(Protocol):
    def close(self) -> None: ...
