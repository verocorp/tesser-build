from __future__ import annotations

import tesser.domain as ts


class Link(ts.ValueObject):

    slug: str
    target_url: str

    def __init__(self, slug: str, target_url: str) -> None:
        object.__setattr__(self, "slug", slug)
        object.__setattr__(self, "target_url", target_url)


class RecordedVerdict(ts.ValueObject):

    target_url: str
    allowed: bool
    reason: str

    def __init__(self, target_url: str, allowed: bool, reason: str) -> None:
        object.__setattr__(self, "target_url", target_url)
        object.__setattr__(self, "allowed", allowed)
        object.__setattr__(self, "reason", reason)


class LinkVerdict(ts.ValueObject):

    slug: str
    target_url: str
    allowed: bool
    reason: str

    def __init__(self, slug: str, target_url: str, allowed: bool, reason: str) -> None:
        object.__setattr__(self, "slug", slug)
        object.__setattr__(self, "target_url", target_url)
        object.__setattr__(self, "allowed", allowed)
        object.__setattr__(self, "reason", reason)


@ts.function
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
