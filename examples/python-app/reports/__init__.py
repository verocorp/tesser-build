"""reports — the cross-context READ as its own (small) bounded context (Moment 2).

A cross-context read that belongs to neither source context gets its own
context ABOVE both peers: it composes their public ``Client``s and joins their
data. The cycle is avoided by DEPENDENCY DIRECTION — reports reads campaign and
linkpolicy, nothing imports reports — not by any special "orchestrator role";
reports has the same anatomy as its siblings (domain owns the join/ordering
semantics; seam, application, wiring; adapters optional, because it reaches
peers only through the injected ``Client``s). It exists here — not inside
``linkpolicy`` (where the verdicts live) — because putting it there would force
``linkpolicy -> campaign`` and close a cycle.

The package top level is the public seam: the ``Client`` Protocol and its
primitive-leaved DTOs, and nothing else.
"""

from reports.client import Client, LinkVerdictView

__all__ = ["Client", "LinkVerdictView"]
