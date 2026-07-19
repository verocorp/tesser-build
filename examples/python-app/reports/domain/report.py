from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Link:

    slug: str
    target_url: str


@dataclass(frozen=True)
class RecordedVerdict:

    target_url: str
    allowed: bool
    reason: str


@dataclass(frozen=True)
class LinkVerdict:

    slug: str
    target_url: str
    allowed: bool
    reason: str


def join_links_with_verdicts(
    links: tuple[Link, ...], verdicts: tuple[RecordedVerdict, ...]
) -> tuple[LinkVerdict, ...]:
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
