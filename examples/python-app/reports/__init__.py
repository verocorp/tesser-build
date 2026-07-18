"""reports — the app-level cross-context READ (Moment 2).

A read-model/orchestrator that lives ABOVE both contexts: it composes the two
public ``Client``s and joins their data. It owns read-model query semantics (the
join + ordering) but no source-of-truth persistence, and it never reaches past the
public Clients. It exists here — not inside ``linkpolicy`` (where the verdicts
live) — because putting it there would force ``linkpolicy -> campaign`` and close a
cycle. This is the acyclic resolution of a cross-context read.
"""

from reports.reports import LinkVerdictRow, ReportsService

__all__ = ["ReportsService", "LinkVerdictRow"]
