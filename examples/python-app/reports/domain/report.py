"""The reports domain: the read-model semantics this context OWNS — the
left-join of links with recorded verdicts, the default for a link with no
verdict, and the ordering. Pure, and in reports' OWN vocabulary: the peers'
DTOs never reach in here (the application translates them inward, the same
move campaign makes with ``CheckOutcome``).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Link:
    """reports' own word for a short link — slug + destination, nothing more."""

    slug: str
    target_url: str


@dataclass(frozen=True)
class RecordedVerdict:
    """reports' own word for a recorded policy verdict."""

    target_url: str
    allowed: bool
    reason: str


@dataclass(frozen=True)
class LinkVerdict:
    """One row of the report: a link joined with its verdict."""

    slug: str
    target_url: str
    allowed: bool
    reason: str


def join_links_with_verdicts(
    links: tuple[Link, ...], verdicts: tuple[RecordedVerdict, ...]
) -> tuple[LinkVerdict, ...]:
    """Left-join: every link appears exactly once. A link whose destination has
    no recorded verdict defaults to allowed — creation would have failed closed
    on a rejection — with an explicit reason, never a silent blank. Blocked
    rows sort first, then by slug."""
    by_url = {v.target_url: v for v in verdicts}
    rows = [
        LinkVerdict(
            slug=link.slug,
            target_url=link.target_url,
            allowed=by_url[link.target_url].allowed if link.target_url in by_url else True,
            reason=by_url[link.target_url].reason if link.target_url in by_url else "no verdict recorded",
        )
        for link in links
    ]
    return tuple(sorted(rows, key=lambda r: (r.allowed, r.slug)))
